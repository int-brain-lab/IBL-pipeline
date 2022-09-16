import json
import logging
import logging.handlers
import os
from pathlib import Path
from uuid import UUID

from appdirs import site_data_dir, user_log_dir

logging.root.setLevel(logging.getLevelName(os.getenv("LOGLEVEL", "INFO")))


def is_valid_uuid(uuid):
    try:
        UUID(str(uuid))
        return True
    except (ValueError, AttributeError):
        return False


json_replace_map = {"'": '"', "None": '"None"', "True": "true", "False": "false"}


def str_to_dict(string):
    try:
        return json.loads(string)
    except json.decoder.JSONDecodeError:
        # fix the json field before decoding.
        for k, v in json_replace_map.items():
            string = string.replace(k, v)
        return json.loads(string)


def get_data_dir(*folders):
    data_dir = Path(os.getenv("IBL_DATA_DIR", site_data_dir("intbrainlab")))
    data_path = data_dir.joinpath(*folders)
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


def get_log_dir(*folders):
    log_dir = Path(os.getenv("IBL_LOG_DIR", user_log_dir("intbrainlab")))
    log_path = log_dir.joinpath(*folders)
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def get_logger(name="root", level=None):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = os.getenv("LOGLEVEL", "INFO") if level is None else level
    logger.setLevel(level)
    logger.propagate = False
    log_file = get_log_dir(*name.split(".")) / f"{level}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    format_ = (
        "\n%(levelname)-8s | %(asctime)20s.%(msecs)-3d | PID=%(process)-7s | "
        "%(name)-20s %(funcName)20s\n%(message)s"
    )
    datetime = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(datefmt=datetime, fmt=format_, style="%")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=15
    )
    file_handler.setLevel("NOTSET")
    file_handler.setFormatter(formatter)
    print_handler = logging.StreamHandler()
    print_handler.setLevel("NOTSET")
    print_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(print_handler)
    return logger
