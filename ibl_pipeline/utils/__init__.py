
from uuid import UUID
import json


def is_valid_uuid(uuid):
    try:
        UUID(uuid)
        return True
    except (ValueError, AttributeError):
        return False


json_replace_map = {
    "\'": "\"",
    'None': '\"None\"',
    'True': 'true',
    'False': 'false'
}


def str_to_dict(string):
    try:
        return json.loads(string)
    except json.decoder.JSONDecodeError:
        # fix the json field before decoding.
        for k, v in json_replace_map.items():
            string = string.replace(k, v)
        return json.loads(string)
