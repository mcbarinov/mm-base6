from __future__ import annotations

import itertools
from decimal import Decimal
from typing import Any, ClassVar, cast, overload

from mm_mongo import AsyncMongoCollection
from mm_std import Result, synchronized, utc_now

from mm_base6.core.db import DynamicConfig, DynamicConfigType
from mm_base6.core.errors import UnregisteredDynamicConfigError
from mm_base6.core.types import SYSTEM_LOG
from mm_base6.core.utils import get_registered_public_attributes


class DC[T: (str, bool, int, float, Decimal)]:
    _counter = itertools.count()

    def __init__(self, value: T, description: str = "", hide: bool = False) -> None:
        self.value: T = value
        self.description = description
        self.hide = hide
        self.order = next(DC._counter)

    @overload
    def __get__(self, obj: None, obj_type: None) -> DC[T]: ...

    @overload
    def __get__(self, obj: object, obj_type: type) -> T: ...

    def __get__(self, obj: object, obj_type: type | None = None) -> T | DC[T]:
        if obj is None:
            return self
        return cast(T, getattr(DynamicConfigStorage.storage, self.key))

    def __set_name__(self, owner: object, name: str) -> None:
        self.key = name


class DynamicConfigsModel:
    pass


class DynamicConfigDict(dict[str, object]):
    def __getattr__(self, item: str) -> object:
        if item not in self:
            raise UnregisteredDynamicConfigError(item)

        return self.get(item, None)


class DynamicConfigStorage:
    storage = DynamicConfigDict()
    descriptions: ClassVar[dict[str, str]] = {}
    types: ClassVar[dict[str, DynamicConfigType]] = {}
    hidden: ClassVar[set[str]] = set()
    collection: AsyncMongoCollection[str, DynamicConfig]
    system_log: SYSTEM_LOG

    @classmethod
    @synchronized
    async def init_storage[DYNAMIC_CONFIGS: DynamicConfigsModel](
        cls,
        collection: AsyncMongoCollection[str, DynamicConfig],
        dynamic_configs: type[DYNAMIC_CONFIGS],
        system_log: SYSTEM_LOG,
    ) -> DYNAMIC_CONFIGS:
        cls.collection = collection
        cls.system_log = system_log

        for attr in get_attrs(dynamic_configs):
            type_ = get_type(attr.value)
            cls.descriptions[attr.key] = attr.description
            cls.types[attr.key] = type_
            if attr.hide:
                cls.hidden.add(attr.key)

            dv = await collection.get_or_none(attr.key)
            if dv:
                typed_value_res = get_typed_value(dv.type, dv.value)
                # if isinstance(typed_value_res, Ok):
                if typed_value_res.is_ok():
                    cls.storage[attr.key] = typed_value_res.unwrap()
                else:
                    await system_log(
                        "dynamic_config.get_typed_value", {"error": typed_value_res.unwrap_error(), "attr": attr.key}
                    )
            else:  # create rows if not exists
                await collection.insert_one(DynamicConfig(id=attr.key, type=type_, value=get_str_value(type_, attr.value)))
                cls.storage[attr.key] = attr.value

        # remove rows which not in DYNAMIC_CONFIGS
        await collection.delete_many({"_id": {"$nin": get_registered_public_attributes(dynamic_configs)}})
        return cast(DYNAMIC_CONFIGS, cls.storage)

    @classmethod
    async def update(cls, data: dict[str, str]) -> bool:
        result = True
        for key in data:
            if key in cls.storage:
                str_value = data.get(key) or ""  # for BOOLEAN type (checkbox)
                str_value = str_value.replace("\r", "")  # for MULTILINE (textarea do it)
                type_value_res = get_typed_value(cls.types[key], str_value.strip())
                if type_value_res.is_ok():
                    await cls.collection.set(key, {"value": str_value, "updated_at": utc_now()})
                    cls.storage[key] = type_value_res.unwrap()
                else:
                    await cls.system_log("DynamicConfigStorage.update", {"error": type_value_res.unwrap_error(), "key": key})
                    result = False
            else:
                await cls.system_log("DynamicConfigStorage.update", {"error": "unknown key", "key": key})
                result = False
        return result

    @classmethod
    def get_non_hidden_keys(cls) -> set[str]:
        return cls.storage.keys() - cls.hidden

    @classmethod
    def get_type(cls, key: str) -> DynamicConfigType:
        return cls.types[key]


def get_type(value: object) -> DynamicConfigType:
    if isinstance(value, bool):
        return DynamicConfigType.BOOLEAN
    if isinstance(value, str):
        return DynamicConfigType.MULTILINE if "\n" in value else DynamicConfigType.STRING
    if isinstance(value, Decimal):
        return DynamicConfigType.DECIMAL
    if isinstance(value, int):
        return DynamicConfigType.INTEGER
    if isinstance(value, float):
        return DynamicConfigType.FLOAT
    raise ValueError(f"unsupported type: {type(value)}")


def get_typed_value(type_: DynamicConfigType, str_value: str) -> Result[Any]:
    try:
        if type_ == DynamicConfigType.BOOLEAN:
            return Result.ok(str_value.lower() == "true")
        if type_ == DynamicConfigType.INTEGER:
            return Result.ok(int(str_value))
        if type_ == DynamicConfigType.FLOAT:
            return Result.ok(float(str_value))
        if type_ == DynamicConfigType.DECIMAL:
            return Result.ok(Decimal(str_value))
        if type_ == DynamicConfigType.STRING:
            return Result.ok(str_value)
        if type_ == DynamicConfigType.MULTILINE:
            return Result.ok(str_value.replace("\r", ""))
        return Result.err(f"unsupported type: {type_}")
    except Exception as e:
        return Result.err(e)


def get_str_value(type_: DynamicConfigType, value: object) -> str:
    if type_ is DynamicConfigType.BOOLEAN:
        return "True" if value else ""
    return str(value)


# noinspection DuplicatedCode
def get_attrs(dynamic_configs: type[DynamicConfigsModel]) -> list[DC[Any]]:
    attrs: list[DC[Any]] = []
    keys = get_registered_public_attributes(dynamic_configs)
    for key in keys:
        field = getattr(dynamic_configs, key)
        if isinstance(field, DC):
            attrs.append(field)
    attrs.sort(key=lambda x: x.order)
    return attrs
