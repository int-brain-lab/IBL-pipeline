import os

import datajoint as dj

_one = None

dj.config["enable_python_native_blobs"] = True

mode = dj.config.get("custom", {}).get("database.mode", "")

if mode == "test":
    dj.config["database.prefix"] = "test_"
elif mode == "update":
    dj.config["database.prefix"] = "update_"


schema = dj.schema("ibl_storage")


@schema
class S3Access(dj.Manual):
    definition = """
    s3_id:  tinyint   # unique id for each S3 pair
    ---
    access_key: varchar(128)   # S3 access key
    secret_key: varchar(128)   # S3 secret key
    """


# attempt to get S3 access/secret key from different sources
access_key = os.environ.get("S3_ACCESS")
secret_key = os.environ.get("S3_SECRET")

if (access_key is None or secret_key is None) and len(S3Access.fetch()) > 0:
    # if there are multiple entries in S3, it won't work
    access_key, secret_key = S3Access.fetch1("access_key", "secret_key")


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
        location=root + "/ephys",
    ),
    "plotting": dict(
        protocol="s3",
        endpoint="s3.amazonaws.com",
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        location=root + "/plotting",
    ),
}


try:
    from one.api import OneAlyx
except ImportError:
    print("ONE-api not set up")
    one = False
else:
    try:
        one = OneAlyx(silent=True)
    except ConnectionError:
        # by-pass error in removing the old format .one_params
        one = OneAlyx(silent=True)
