import contextlib
import json
import os
from datetime import datetime
from pathlib import Path
from shutil import rmtree
from urllib.error import HTTPError

import numpy as np
import pandas as pd
from dotenv import dotenv_values
from one.api import ONE

ONE_PARAMS_DESTINATION = Path.home() / ".one_params"
DEFAULT_DOT_ENV_FILE = (Path(__file__).parent / ".." / ".env").resolve()
ROOT_EXPERIMENTAL_FOLDER = Path.home() / "Datasets" / "iblalyx" / "test-one"
ROOT_EXPERIMENTAL_FOLDER.mkdir(parents=True, exist_ok=True)


def get_one_params_from_env_file(dot_env_file):
    """Load ONE params from .env file.

    Args:
        dot_env_file (str): Path to .env file

    Returns:
        dict: ONE specific parameters
    """

    content = """
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
    alyx_vars = dotenv_values(dot_env_file)
    deliml = "{{"
    delimr = "}}"
    for tag, value in alyx_vars.items():
        content = content.replace(f"{deliml}{tag}{delimr}", value or "null")
    params = json.loads(content)
    params = {k: None if v and v.startswith("{{") else v for k, v in params.items()}
    return params


def write_one_params(dot_env_file, folder=None):
    """Write ONE specific parameters from .env file to disk.

    Args:
        dot_env_file (str): Path to .env file
        folder (str, optional): Where to store .one_params file. Defaults to None.

    Returns:
        Path: path to .one_params file
    """
    params = get_one_params_from_env_file(dot_env_file)
    dot_one_file = Path(folder) / ".one_params" if folder else ONE_PARAMS_DESTINATION
    dot_one_file.unlink(True)
    dot_one_file.touch(0o664)
    with open(dot_one_file, "w") as fc:
        json.dump(params, fc, indent=2)
    return dot_one_file


def connect_alyx(base_url=None, dot_one_file=None):
    """Initiate a connection to Alyx via one.api and return a connection object.

    one = OneAlyx(password="******", username="ibl_dev", base_url="http://localhost:8000", silent=True)

    Args:
        base_url (str): A URL to connect to, such as
            `localhost:8000` or `alyx.internationalbrainlab.org`
        dot_one_file (Path, optional): File to .one_params file.
            Defaults to None (home).

    Returns:
        OneAlyx: An one.api connection object used to interact with an Alyx database
    """

    # the arguments base_url and password are the minimum required if
    # the rest of ~/.one_params is filled out correctly
    one_args = {
        "base_url": base_url or "http://localhost:8000",
        "silent": True,
    }

    dot_one_file = Path(dot_one_file or ONE_PARAMS_DESTINATION)

    if dot_one_file.exists():
        print(f"#~ INFO: This will remove existing file at '{dot_one_file}'")
        with open(dot_one_file, "r") as jsf:
            params = json.load(jsf)
        one_args = {
            "username": params.get("ALYX_LOGIN", os.getenv("ALYX_LOGIN", None)),
            "password": params.get("ALYX_PWD", os.getenv("ALYX_PWD", None)),
            **one_args,
            "base_url": params.get("ALYX_URL", one_args["base_url"]),
        }

    print("#~ INFO: Initiating connection to Alyx")
    return ONE(**one_args)


def connect_localhost(dot_env_file="", reset=False):
    """Connect to Alyx via ONE using localhost defaults.

    Args:
        dot_env_file (str): Path to .env file
        reset (bool, optional): Remove `.one` folder at user path. Defaults to False.

    Raises:
        FileNotFoundError: Can't find .env file.

    Returns:
        ONE: one.api object
    """
    if not dot_env_file:
        dot_env_file = DEFAULT_DOT_ENV_FILE
    dot_env_file = Path(dot_env_file).expanduser().resolve()
    if not dot_env_file.exists():
        raise FileNotFoundError(f"can't find *.env file {dot_env_file}")
    dot_one_file = write_one_params(dot_env_file)
    if reset:
        rmtree(Path.home() / ".one", ignore_errors=True)
    oh_in_ee = connect_alyx(dot_one_file=dot_one_file)
    repr(oh_in_ee)
    return oh_in_ee


def create_project(one, user="defaultuser"):
    project = one.alyx.rest(
        "projects",
        "create",
        data=dict(name="main", users=[user]),
    )

    # create the repository with name 'local' (NB: an URL is needed here, even if it is rubbish as below)
    repo = one.alyx.rest(
        "data-repository",
        "create",
        data=dict(name="local", data_url="http://anyurl.org"),
    )

    with contextlib.suppress(HTTPError):
        # assign the repository to 'defaultlab'
        one.alyx.rest("labs", "create", data=dict(name="defaultlab"))

    one.alyx.rest(
        "labs", "partial_update", id="defaultlab", data=dict(repositories=["local"])
    )


def create_subject(one, user="defaultuser"):
    # create a subject
    one.alyx.rest(
        "subjects",
        "create",
        data=dict(nickname="Algernon", lab="defaultlab", project="main", sex="M"),
    )


def create_session(one, user="defaultuser"):
    # create a session
    session_dict = dict(
        subject="Algernon",
        number=1,
        lab="defaultlab",
        task_protocol="test registration",
        project="main",
        start_time=str(datetime.now()),
        users=[user],
    )
    session = one.alyx.rest("sessions", "create", data=session_dict)
    # this is the experimental id that will be used to retrieve the data later
    eid = session["url"][-36:]

    # create a trials table in the relative folder defaultlab/Subjects/Algernon/yyyy-mm-dd/001
    session_path = ROOT_EXPERIMENTAL_FOLDER.joinpath(
        session["lab"],
        "Subjects",
        session["subject"],
        session["start_time"][:10],
        str(session["number"]).zfill(3),
    )
    alf_path = session_path.joinpath("alf")
    alf_path.mkdir(parents=True, exist_ok=True)
    ntrials = 400
    trials = pd.DataFrame(
        {"choice": np.random.randn(ntrials) > 0.5, "value": np.random.randn(ntrials)}
    )
    trials.to_parquet(alf_path.joinpath("trials.table.pqt"))

    # register the dataset
    r = {
        "created_by": user,
        "path": session_path.relative_to((session_path.parents[2])).as_posix(),
        "filenames": ["alf/trials.table.pqt"],
        "name": "local",  # this is the repository name
    }
    response = one.alyx.rest("register-file", "create", data=r, no_cache=True)
    return response


def run_query(one):
    session = one.alyx.rest("sessions", "list", subject="Algernon")[-1]
    eid = session["id"]
    # TODO: !!NOT WORKING
    datasets = one.list_datasets(eid)
    # from the client side, provided with only the eids we reconstruct the full dataset paths
    local_path = ROOT_EXPERIMENTAL_FOLDER.joinpath(*one.eid2path(eid).parts[-5:])
    local_files = [local_path.joinpath(dset) for dset in datasets]
    print(local_files)


if __name__ == "__main__":
    one = connect_localhost(reset=True)
    params = get_one_params_from_env_file(DEFAULT_DOT_ENV_FILE)
    user = params["ALYX_LOGIN"]
    create_subject(one, user)
    session = create_session(one, user)
    response = run_query(one)
