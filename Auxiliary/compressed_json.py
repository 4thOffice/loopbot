import base64
import gzip
import json


def encode_json_to_string(json_object: dict):
    return base64.b64encode(
        gzip.compress(
            json.dumps(json_object, indent=None, separators=(',', ':')).encode()
        )
    ).decode().replace("/", "_").replace("+", "-")


def decode_from_json_string(compressed_json_string: str):
    return json.loads(
        gzip.decompress(
            base64.b64decode(
                compressed_json_string.replace("_", "/").replace("-", "+").encode()
            )
        ).decode()
    )
