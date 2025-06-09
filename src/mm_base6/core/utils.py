from collections.abc import Mapping
from decimal import Decimal

import tomlkit
from tomlkit.items import Float, Trivia


def encode_decimal(value: object) -> Float:
    if isinstance(value, Decimal):
        return Float(value=float(value), trivia=Trivia(), raw=str(value))
    raise TypeError(f"Cannot convert {type(value)} to TOML item")


tomlkit.register_encoder(encode_decimal)


def toml_dumps(data: Mapping[str, object], sort_keys: bool = False) -> str:
    return tomlkit.dumps(data, sort_keys=sort_keys)


def toml_loads(string: str | bytes) -> tomlkit.TOMLDocument:
    return tomlkit.loads(string)


def get_registered_public_attributes(obj: object) -> list[str]:
    return [x for x in dir(obj) if not x.startswith("_")]
