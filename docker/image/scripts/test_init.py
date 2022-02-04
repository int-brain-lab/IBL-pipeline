import os
import sys
import tempfile
from pathlib import Path
from shutil import copyfile, rmtree


def load_env(file):
    with open(file) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            print(line)
            key, value = line.strip().split("=", 1)
            os.environ[key] = value


def resolve_path(path):
    return Path(path).expanduser().resolve()


def make_dirs(ibl_path_root=None, remove=False, host="private"):
    if ibl_path_root is None:
        ibl_path_root = tempfile.gettempdir() + "/int-brain-lab"

    ibl_path_root = resolve_path(ibl_path_root)

    if remove:
        rmtree(ibl_path_root, ignore_errors=True)
        rmtree(resolve_path("~/.one"), ignore_errors=True)

    ibl_path_data = ibl_path_root / "data"
    ibl_path_alyx = ibl_path_data / "alyx" / "cache" / host
    ibl_path_shared = ibl_path_root / "shared"

    ibl_path_alyx.mkdir(parents=True, exist_ok=True)
    ibl_path_shared.mkdir(parents=True, exist_ok=True)

    return {
        "root": ibl_path_root,
        "data": ibl_path_data,
        "shared": ibl_path_shared,
        "alyx": ibl_path_alyx,
    }


def env_test(
    ibl_path_root="~/Datasets/int-brain-lab", env_file="", host="private", remove=False
):
    this_dir = Path(__file__).parent

    # load environment variables from .env file
    if not env_file:
        env_file = this_dir / ".." / "ibldatajoint" / ".env"
    env_file = resolve_path(env_file)
    if not env_file.exists():
        raise FileNotFoundError("wrong path for .env file")
    load_env(env_file.resolve())

    # make folder structure
    dirs = make_dirs(ibl_path_root, remove, host)
    os.environ["IBL_PATH_ROOT"] = dirs["root"].as_posix()
    os.environ["IBL_PATH_DATA"] = dirs["data"].as_posix()
    os.environ["IBL_PATH_SHARED"] = dirs["shared"].as_posix()

    # copy template to ibl root
    tmp_json = dirs["root"] / "config.json"
    tmp_json.unlink(True)
    copyfile(this_dir / "config.json", tmp_json)

    # copy
    tmp_local = dirs["root"] / "local.one_params"
    tmp_local.unlink(True)
    local_one_params = this_dir / ".." / ".." / "shared" / "local.one_params"
    copyfile(local_one_params, tmp_local)

    if not this_dir.as_posix() in sys.path:
        sys.path.append(this_dir.as_posix())

    from config_init import (
        _dest_dj_config_path,
        _dest_one_params_path,
        dj_config_mappings,
        get_config,
        init_dj_config,
        init_one_alyx,
        one_params_mappings,
    )

    params = get_config(tmp_local, "alyx", one_params_mappings(), None)
    config = get_config(tmp_json, "datajoint", dj_config_mappings(), None)

    init_one_alyx(host)
    _dest_one_params_path.unlink(True)

    init_dj_config(tmp_json)
    copyfile(_dest_dj_config_path, dirs["root"] / "dj_local_conf.json")
    _dest_dj_config_path.unlink(True)

    return dirs
