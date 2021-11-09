"""Setup DataJoint config and ONE-api connection

Initialize configuration files for DataJoint and ONE and their connections.

Usage as a script:

    python config_init.py ...

See script help messages:

    python config_init.py --help

(or the functions `init_dj_config` or `init_one_alyx` can be imported directly)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence, Union, Optional

import one.params
from one.api import OneAlyx


StrVec = Union[list[str], str, None]
StrPath = Union[str, Path]

# global environment variables
IBL_PATH_ROOT = os.getenv("IBL_PATH_ROOT", "/int-brain-lab")
IBL_PATH_DATA = os.getenv("IBL_PATH_DATA", "/int-brain-lab/data")
ALYX_PORT = os.getenv("ALYX_PORT", "8000")

# alyx urls based on public/private or docker service access
_alyx_urls = {
    "public": {
        "url": "https://openalyx.internationalbrainlab.org",
        "port": "openalyx.internationalbrainlab.org",
    },
    "private": {
        "url": "https://alyx.internationalbrainlab.org",
        "port": "alyx.internationalbrainlab.org",
    },
    "local": {"url": "http://localhost", "port": f"{ALYX_PORT}"},
    "dev": {"url": "http://alyx", "port": f"{ALYX_PORT}"},
}

# default template file to use to populate config parameters for datajoint and alyx
_default_json_template = Path(IBL_PATH_ROOT) / "template.ingest.json"
_default_local_one_params = Path(IBL_PATH_ROOT) / "shared" / "local.one_params"

# where ONE-api will look for first-time-use parameters
_dest_one_params_path = Path.home() / ".one_params"

# where DataJoint will look for configuration file
_dest_dj_config_path = Path.home() / ".datajoint_config.json"


def parse_args(args: Sequence[str]) -> argparse.Namespace:
    """
    Parse command line parameters

    :param args: Command line parameters as list of strings (for example  `["--help"]`)
    :type args: Sequence[str]
    :return: A Namespace of command line parameters
    :rtype: argparse.Namespace
    """

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "-t",
        "--alyxhost",
        dest="alyx_host",
        help="Type of Alyx host to connect to",
        type=str,
        default="dev",
        choices=list(_alyx_urls.keys()),
    )

    parser.add_argument(
        "-o",
        "--onepar",
        dest="one_file",
        help="Path to a JSON file with ONE parameters. "
        "Must be accessible from within the container. "
        "Contents will be temporarily saved to '~/.one_params'. ",
        type=str,
        default=None,
    )

    parser.add_argument(
        "-d",
        "--djcfg",
        dest="dj_cfg_file",
        help="path to a JSON file for DataJoint configuration. "
        "Must be accessible from within the container. "
        "Contents will be saved to '~/.datajoint_config.json'. "
        "Leave blank to use default template JSON.",
        type=str,
        default=_default_json_template.as_posix(),
    )

    return parser.parse_args(args)


def _read_file(file: StrPath) -> str:
    """
    Return a string representation of a file that has c-style comments removed

    :param file: A text file
    :type file: StrPath
    :raises FileNotFoundError: Path from `file` must exist
    :return: string content of the text file
    :rtype: str
    """
    file = Path(file)
    if not file.exists():
        raise FileNotFoundError(file.as_posix())
    with open(file, "r") as fc:
        # ignore c-style comments
        f_strs = "".join(line for line in fc if not line.startswith("//"))
    return f_strs


# TODO: should take a nested list and be recursive
def assert_keys(obj: dict, keys: StrVec = None) -> None:
    if keys is not None:
        if isinstance(keys, str):
            keys = [keys]
        if not all(key in obj for key in keys):
            raise KeyError(*keys)


def insert_envars(mappings: dict) -> dict:
    for tag, env in mappings.items():
        mappings[tag] = os.getenv(env)
        if mappings[tag] is None:
            print(f"#~ INFO: Environment variable '{env}' is empty.")

    return mappings


def dj_config_mappings() -> dict:
    return insert_envars(
        {
            "%DJ_HOST%": "DJ_HOST",
            "%DJ_PASS%": "DJ_PASS",
            "%DJ_MODE%": "DJ_MODE",
            "%DJ_USER%": "DJ_USER",
            "%S3_ACCESS%": "S3_ACCESS",
            "%S3_SECRET%": "S3_SECRET",
            "%S3_MIGRATE_BUCKET%": "S3_MIGRATE_BUCKET",
            "%S3_ROOT_PATH%": "S3_ROOT_PATH",
            "%IBL_PATH_ROOT%": "IBL_PATH_ROOT",
            "%IBL_PATH_DATA%": "IBL_PATH_DATA",
            "%IBL_PATH_SHARED%": "IBL_PATH_SHARED",
        }
    )


def one_params_mappings() -> dict:
    return insert_envars(
        {
            "%ALYX_LOGIN%": "ALYX_LOGIN",
            "%ALYX_PWD%": "ALYX_PWD",
            "%ALYX_URL%": "ALYX_URL",
            "%CACHE_DIR%": "CACHE_DIR",
            "%HTTP_DATA_SERVER%": "HTTP_DATA_SERVER",
            "%HTTP_DATA_SERVER_LOGIN%": "HTTP_DATA_SERVER_LOGIN",
            "%HTTP_DATA_SERVER_PWD%": "HTTP_DATA_SERVER_PWD",
        }
    )


def replace_tags(cfg_str: str, mappings: dict) -> str:
    """
    Take a long string with multiple tags (e.g., %TAG%) and replace them with matching
    values found in `mappings`

    :param cfg_str: A long string with tags
    :type cfg_str: str
    :param mappings: key-value pairs of values to use to replace tags
    :type mappings: dict
    :return: Input string but with tags replaced
    :rtype: str
    """
    for tag, value in mappings.items():
        cfg_str = cfg_str.replace(tag, value or "")
    return cfg_str.replace('""', "null")


def get_config(
    file: Path, cfg_set: str, mappings: dict, must_exist: StrVec = None
) -> dict:
    """
    Read a JSON config file and replace tags with the provided mappings

    :param file: Path to a JSON file
    :type file: Path
    :param cfg_set: Top-level key, e.g., "alyx" or "datajoint"
    :type cfg_set: str
    :param mappings: Dictionary of '%TAG%':'value' mappings
    :type mappings: dict
    :param must_exist: A list keys that just exist in the config, defaults to None
    :type must_exist: StrVec, optional
    :return: JSON configuration as dict with tags replaced.
    :rtype: dict
    """
    cfg_str = replace_tags(_read_file(file), mappings)
    config = json.loads(cfg_str)
    config = config.get(cfg_set, config)
    assert_keys(config, must_exist)

    return config


def connect_alyx(base_url: str) -> OneAlyx:
    """
    Initiate an Alyx connection via one.api and return a connection object.

    After the first connection, `OneAlyx` will pull configuration from `~/.one/.<url>`.
     If connecting using a `.one_params` file it must already be in your **home**
     directory, and the file **must** contain:
      `ALYX_URL`
      `ALYX_LOGIN`
      `ALYX_PWD`
      `HTTP_DATA_SERVER`
      `HTTP_DATA_SERVER_LOGIN`
      `HTTP_DATA_SERVER_PWD`
      `CACHE_DIR`

    :param base_url: A URL to connect to, such as `localhost:8000` or `alyx.internationalbrainlab.org`
    :type base_url: str
    :return: A connection object used to interact with an Alyx database
    :rtype: one.api.OneAlyx
    """
    # the arguments base_url and password are the minimum required if
    # the rest of ~/.one_params is filled out correctly
    one_args = {
        "base_url": base_url,
        "silent": True,
    }

    if _dest_one_params_path.exists():
        print("#~ INFO: Removing existing ~/.one_params file")
        with open(_dest_one_params_path, "r") as jsf:
            params = json.load(jsf)
        one_args = {"password": params.get("ALYX_PWD", None), **one_args}

    print("#~ INFO: Initiating connection to Alyx")
    return OneAlyx(**one_args)


def init_one_alyx(host: str = "dev", file: Optional[Path] = None) -> None:
    # using environment variables instead of file
    if file is None:
        if host in ["private", "public"]:
            file = _default_json_template
        elif host in ["dev", "local"]:
            file = _default_local_one_params
        else:
            raise FileExistsError("'host' must be valid if file not present")

    file = Path(file)
    params = get_config(
        file or _default_local_one_params,
        cfg_set="alyx",
        mappings=one_params_mappings(),
        must_exist=[
            "ALYX_LOGIN",
            "ALYX_PWD",
            "ALYX_URL",
            "HTTP_DATA_SERVER_LOGIN",
            "HTTP_DATA_SERVER_PWD",
            "HTTP_DATA_SERVER",
        ],
    )

    # use ServerNameAlias if accessing alyx from a diff container on the same network
    if host == "dev" and "localhost" in params["ALYX_URL"]:
        params["ALYX_URL"] = params["ALYX_URL"].replace("localhost", "alyx")
        params["CACHE_DIR"] = None

    # make cache dir based on type of host connection
    if not params.get("CACHE_DIR"):
        cache_dir = Path(IBL_PATH_DATA) / "alyx" / "cache" / host
        cache_dir.mkdir(0o776, True, True)
        params["CACHE_DIR"] = cache_dir.as_posix()

    # if CACHE_DIR is pre set in .one_params file, make sure it exists
    if not Path(params["CACHE_DIR"]).exists():
        raise NotADirectoryError(
            f'CACHE_DIR: {params["CACHE_DIR"]}, custom path must exist'
        )

    # remove existing ~/.one_params if any, then write params to home
    _dest_one_params_path.unlink(True)
    _dest_one_params_path.touch(0o664)
    with open(_dest_one_params_path, "w") as f:
        json.dump(params, f)

    # initialize connection (will create ~/.one/* and cache info)
    connect_alyx(params["ALYX_URL"])


def init_dj_config(file: Path) -> None:
    config = get_config(
        file,
        cfg_set="datajoint",
        mappings=dj_config_mappings(),
        must_exist=[
            "database.host",
            "database.password",
            "database.user",
            "stores",
            "custom",
        ],
    )
    if not config.get("connection.charset"):
        config["connection.charset"] = ""
    _dest_dj_config_path.unlink(True)
    _dest_dj_config_path.touch(0o664)
    with open(_dest_dj_config_path, "w") as f:
        json.dump(config, f)


def main(args: Sequence[str]) -> None:
    """
    Wrapper allowing worker functions to be called from CLI

    :param args: command line parameters as list of strings (for example  ``["--help"]``)
    :type args: Sequence[str]
    """
    args = parse_args(args)
    init_one_alyx(args.alyx_host, args.one_file)
    init_dj_config(Path(args.dj_cfg_file))


def run() -> None:
    """
    Calls :func:`main` passing the CLI arguments extracted from `sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
