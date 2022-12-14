import os
import re
from pathlib import Path

import datajoint as dj
from appdirs import user_cache_dir

from ibl_pipeline.utils import get_logger as _logger

# mode = dj.config.get("custom", {}).get("database.mode", os.getenv("DJ_MODE", ""))
mode = ""

if mode == "test":
    dj.config["database.prefix"] = "test_"
elif mode == "update":
    dj.config["database.prefix"] = "update_"
else:
    dj.config["database.prefix"] = os.getenv(
        "DJ_DATABASE_PREFIX",
        dj.config.get(
            "database.prefix", dj.config.get("custom", {}).get("database.prefix", "")
        ),
    )

dj.config["enable_python_native_blobs"] = True

access_key = os.getenv("S3_ACCESS")
secret_key = os.getenv("S3_SECRET")

if mode == "public":
    bucket = "ibl-dj-external-public"
    root = "/public"
else:
    bucket = "ibl-dj-external"
    root = ""

dj.config["stores"] = {
    "ephys": dict(
        protocol="s3",
        endpoint="s3.amazonaws.com",
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        location=f"{root}/ephys",
    ),
    "plotting": dict(
        protocol="s3",
        endpoint="s3.amazonaws.com",
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        location=f"{root}/plotting",
    ),
}

ibl_logger = _logger("ibl_pipeline")


def get_one_api_public(password=None, url="https://openalyx.internationalbrainlab.org"):
    try:
        from one.api import OneAlyx
    except ImportError as error:
        print(error)
        print("'one-api' package not imported.")
        one = None
    else:
        base_url = (
            dj.config.get("custom", {}).get(
                "database.alyx.url", os.getenv("ALYX_URL", None)
            )
            or url
        )
        cache_dir = (
            Path(os.getenv("CACHE_DIR") or user_cache_dir("ibl"))
            / "ONE"
            / re.sub(r"^https*:/+", "", base_url)
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            one = OneAlyx(
                mode="remote",
                wildcards=True,
                base_url=base_url,
                password=password or "international",
                silent=True,
                cache_dir=cache_dir,
            )
            one.refresh_cache("refresh")
        except ConnectionError:
            print(
                "Could not connect to Alyx. Using 'openalyx.internationalbrainlab.org'"
            )
            one = OneAlyx(
                mode="auto",
                wildcards=True,
                base_url="https://openalyx.internationalbrainlab.org",
                password="international",
                silent=True,
                cache_dir=cache_dir,
            )

    return one


one = get_one_api_public()
