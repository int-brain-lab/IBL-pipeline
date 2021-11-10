import os
import tempfile
import json
from shutil import copyfile, rmtree
from pathlib import Path


def load_env(file):
    with open(file) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            print(line)
            key, value = line.strip().split("=", 1)
            os.environ[key] = value


def env_test():
    this_dir = Path(__file__).parent
    env_file = this_dir / ".." / "ingest" / ".env"
    ingest_json = this_dir / "template.ingest.json"
    local_one_params = this_dir / ".." / ".." / "shared" / "local.one_params"

    if not env_file.exists():
        raise FileNotFoundError("wrong path for .env file")

    # load environment variables from .env file
    load_env(env_file.resolve())

    # temp dir for cache and ibl root
    tempd = Path(tempfile.gettempdir())
    ibl_path_root = tempd / "int-brain-lab"
    rmtree(ibl_path_root, ignore_errors=True)
    rmtree("~/.one", ignore_errors=True)
    ibl_path_root.mkdir(parents=True, exist_ok=True)

    os.environ["IBL_PATH_ROOT"] = ibl_path_root.as_posix()
    os.environ["IBL_PATH_DATA"] = (ibl_path_root / "data").as_posix()

    tmp_json = ibl_path_root / "template.ingest.json"
    tmp_json.unlink(True)
    copyfile(ingest_json, tmp_json)

    tmp_local = ibl_path_root / "local.one_params"
    tmp_local.unlink(True)
    copyfile(local_one_params, tmp_local)

    from config_init import (
        get_config,
        init_one_alyx,
        init_dj_config,
        one_params_mappings,
        dj_config_mappings,
        _dest_one_params_path,
        _dest_dj_config_path,
    )

    params = get_config(tmp_local, "alyx", one_params_mappings(), None)
    config = get_config(tmp_json, "datajoint", dj_config_mappings(), None)

    init_dj_config(tmp_json)
    init_one_alyx("local", tmp_local)

    _dest_one_params_path.unlink(True)
    _dest_dj_config_path.unlink(True)
