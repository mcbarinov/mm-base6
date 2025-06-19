from collections.abc import Mapping
from decimal import Decimal

import tomlkit
from tomlkit.items import Float, Item, Trivia


def custom_encoder(value: object) -> Item:
    if isinstance(value, Decimal):
        return Float(value=float(value), trivia=Trivia(), raw=str(value))
    raise TypeError(f"Cannot convert {type(value)} to TOML item")


tomlkit.register_encoder(custom_encoder)


def toml_dumps(data: Mapping[str, object], sort_keys: bool = False) -> str:
    filtered_data = {k: v for k, v in data.items() if v is not None}
    return tomlkit.dumps(filtered_data, sort_keys=sort_keys)


def toml_loads(string: str | bytes) -> tomlkit.TOMLDocument:
    return tomlkit.loads(string)


def get_registered_public_attributes(obj: object) -> list[str]:
    return [x for x in dir(obj) if not x.startswith("_")]
