#!/usr/local/bin/python
"""Initiate ONE Connection

    %(prog)s --help
"""
import json
import logging as log
import os
import sys
from pathlib import Path
from shutil import rmtree
from textwrap import dedent

from datajoint_utilities.cmdline import ArgparseBase, HelpFmtDefaultsDocstringMeta
from dotenv import dotenv_values
from one.api import OneAlyx
from one.params import _key_from_url, get_params_dir

log.basicConfig(
    format="[%(asctime)s %(process)d %(processName)s "
    "%(levelname)s %(name)s]: %(message)s",
    datefmt="%z %Y-%m-%d %H:%M:%S",
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
)

VERSION = "0.0.1"
ROOT_IBL_PATH = Path(os.getenv("IBL_PATH_ROOT", "/int-brain-lab"))
ONE_PARAMS_DESTINATION = Path.home() / ".one_params"
DEFAULT_DOT_ENV_FILE = ROOT_IBL_PATH / "ibldatajoint.env"


class ParseArgs(ArgparseBase):
    def __init__(self, sysargv):
        super().__init__(
            sysargv,
            "ONE-connect",
            VERSION,
            __doc__,
            HelpFmtDefaultsDocstringMeta,
        )

    def make(self):
        self.parser.add_argument(
            "--env-file",
            dest="env_file",
            help=".env file to load.",
            type=str,
            default=DEFAULT_DOT_ENV_FILE,
        )
        self.parser.add_argument(
            "--reset-one",
            dest="reset_one",
            help="Delete existing .one directory at user home.",
            action="store_true",
        )


def _json_write(file, data, indent=4, mode="w"):
    with open(file, mode) as fc:
        json.dump(data, fc, indent=indent)
    return file


def _json_load(file, mode="r"):
    with open(file, mode) as fc:
        return json.load(fc)


def get_one_params_from_env_file(dot_env_file):
    """Load ONE params from .env file.

    Args:
        dot_env_file (str): Path to .env file

    Returns:
        dict: ONE specific parameters
    """

    content = dedent(
        """
        {
            "ALYX_LOGIN": "{{ALYX_LOGIN}}",
            "ALYX_PWD": "{{ALYX_PWD}}",
            "ALYX_URL": "{{ALYX_URL}}",
            "CACHE_DIR": "{{CACHE_DIR}}",
            "HTTP_DATA_SERVER": "{{HTTP_DATA_SERVER}}",
            "HTTP_DATA_SERVER_LOGIN": "{{HTTP_DATA_SERVER_LOGIN}}",
            "HTTP_DATA_SERVER_PWD": "{{HTTP_DATA_SERVER_PWD}}"
        }
        """
    )
    env = dotenv_values(dot_env_file)
    deliml = "{{"
    delimr = "}}"
    for key, value in env.items():
        content = content.replace(f"{deliml}{key}{delimr}", value or "null")
    params = json.loads(content)
    params = {
        k: None if v and (v.startswith(deliml) or v == "null") else v
        for k, v in params.items()
    }
    return params


def write_one_params(params, folder=None):
    """Write ONE specific parameters from .env file to disk.

    Args:
        dot_env_file (str): Path to .env file
        folder (str, optional): Where to store .one_params file. Defaults to None.

    Returns:
        Path: path to .one_params file
    """
    dot_one_file = Path(folder) / ".one_params" if folder else ONE_PARAMS_DESTINATION
    dot_one_file.unlink(True)
    dot_one_file.touch(0o664)
    return _json_write(dot_one_file, params)


def connect_alyx(base_url="http://localhost:8000", dot_one_file=None):
    """Initiate a connection to Alyx via one.api and return a connection object.

    one = OneAlyx(password="******",
                  username="ibl_dev",
                  base_url="http://localhost:8000",
                  silent=True)

    Args:
        base_url (str): A URL to connect to, such as
            `localhost:8000` or `alyx.internationalbrainlab.org`
        dot_one_file (Path, optional): File to .one_params file.
            Defaults to None (home).

    Returns:
        OneAlyx: An one.api connection object used to interact with an Alyx database
    """
    one_args = {
        "base_url": base_url,
        "silent": True,
    }
    params = {}
    dot_one_file = Path(dot_one_file or ONE_PARAMS_DESTINATION)
    if dot_one_file.exists():
        log.debug(f"loading .one_params file: '{dot_one_file}'")
        params |= _json_load(dot_one_file)
        param_args = {
            "base_url": params.get("ALYX_URL", os.getenv("ALYX_URL", None)),
            "username": params.get("ALYX_LOGIN", os.getenv("ALYX_LOGIN", None)),
            "password": params.get("ALYX_PWD", os.getenv("ALYX_PWD", None)),
            "cache_dir": params.get("CACHE_DIR", os.getenv("CACHE_DIR", None)),
        }
        one_args |= {k: v for k, v in param_args.items() if v}

    log.debug("connecting to Alyx")
    oh_in_ee = OneAlyx(**one_args)

    params_name = _key_from_url(one_args["base_url"])
    params_file = get_params_dir() / f".{params_name}"
    if not params_file.exists():
        raise FileNotFoundError(
            "ONE parameters file not created and no connection made."
        )
    one_params = _json_load(params_file)
    if fill_missing := {k: v for k, v in params.items() if k in one_params}:
        log.debug(f"filling in missing parameters '{params_file}'")
        one_params |= fill_missing
        _json_write(params_file, one_params)
        if cache_dir := params.get("CACHE_DIR", os.getenv("CACHE_DIR", None)):
            dot_caches_file = get_params_dir() / ".caches"
            if dot_caches_file.exists():
                dot_caches = _json_load(dot_caches_file)
                if params_name in dot_caches["CLIENT_MAP"]:
                    dot_caches["CLIENT_MAP"][params_name] = cache_dir
                    log.debug(f"rewriting cache entry '{dot_caches_file}'")
                    _json_write(dot_caches_file, dot_caches)
        log.debug("reconnecting to Alyx")
        oh_in_ee = OneAlyx(base_url=one_params["ALYX_URL"], silent=True)
    return oh_in_ee


def connect(env_file=DEFAULT_DOT_ENV_FILE, reset_one=False, **kwargs):
    """Connect to Alyx via ONE using localhost defaults.

    Args:
        env_file (str): Path to .env file
        reset (bool, optional): Remove `.one` folder at user path. Defaults to False.

    Raises:
        FileNotFoundError: Can't find .env file.

    Returns:
        ONE: one.api object
    """
    if not env_file:
        raise FileNotFoundError(f".env file cannot be empty '{env_file}'")
    env_file = Path(env_file).expanduser()
    if not env_file.exists():
        raise FileNotFoundError(f"can't find *.env file {env_file}")
    env_file = env_file.resolve()
    log.info(f"Getting ONE parameters from .env file {env_file}")
    params = get_one_params_from_env_file(env_file)
    dot_one_file = write_one_params(params)
    log.info(f"Temporarily saved .one_params {dot_one_file}")
    if reset_one:
        one_dir = get_params_dir()
        log.warning(f"Directory will be deleted!: {one_dir}")
        rmtree(one_dir, ignore_errors=True)
    log.info("Initiating connection to Alyx")
    oh_in_ee = connect_alyx(dot_one_file=dot_one_file)
    log.info(f"Deleting file {dot_one_file}")
    dot_one_file.unlink(True)
    log.info(str(oh_in_ee))
    return oh_in_ee


def cli() -> None:
    """Calls this program, passing along the cli arguments extracted from `sys.argv`.

    This function can be used as entry point to create console scripts.

    Raises:
        SystemExit: End of program execution
    """
    parser = ParseArgs(sys.argv[1:] or ["-v"])
    connect(**parser.args)
    raise SystemExit


if __name__ == "__main__":
    cli()
