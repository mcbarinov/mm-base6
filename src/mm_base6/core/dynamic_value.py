from __future__ import annotations

import asyncio
import base64
import itertools
import pickle  # nosec: B403
from typing import Any, ClassVar, cast, overload

from mm_mongo import AsyncMongoCollection
from mm_std import synchronized, utc_now

from mm_base6.core.db import DynamicValue
from mm_base6.core.errors import UnregisteredDynamicValueError
from mm_base6.core.utils import get_registered_public_attributes


class DV[T]:
    _counter = itertools.count()

    def __init__(self, value: T, description: str = "", persistent: bool = True) -> None:
        self.value = value
        self.description = description
        self.persistent = persistent
        self.order = next(DV._counter)

    @overload
    def __get__(self, obj: None, obj_type: None) -> DV[T]: ...

    @overload
    def __get__(self, obj: object, obj_type: type) -> T: ...

    def __get__(self, obj: object | None, obj_type: type | None = None) -> T | DV[T]:
        if obj is None:
            return self
        return cast(T, getattr(DynamicValueStorage.storage, self.key))

    def __set__(self, instance: object, value: T) -> None:
        setattr(DynamicValueStorage.storage, self.key, value)

    def __set_name__(self, owner: object, name: str) -> None:
        self.key = name


class DynamicValuesModel:
    pass


class DynamicValueDict(dict[str, object]):
    def __getattr__(self, item: str) -> object:
        if item not in self:
            raise UnregisteredDynamicValueError(item)
        return self.get(item)

    def __setattr__(self, key: str, value: object) -> None:
        if key not in self:
            raise UnregisteredDynamicValueError(key)
        if DynamicValueStorage.persistent[key]:
            asyncio.create_task(DynamicValueStorage.update_persistent_value(key, value))  # TODO: is it OK? # noqa: RUF006
        self[key] = value


class DynamicValueStorage:
    storage = DynamicValueDict()
    persistent: ClassVar[dict[str, bool]] = {}
    descriptions: ClassVar[dict[str, str]] = {}
    collection: AsyncMongoCollection[str, DynamicValue]

    @classmethod
    @synchronized
    async def init_storage[DYNAMIC_VALUES: DynamicValuesModel](
        cls, collection: AsyncMongoCollection[str, DynamicValue], dynamic_values: type[DYNAMIC_VALUES]
    ) -> DYNAMIC_VALUES:
        cls.collection = collection
        persistent_keys = []

        for attr in get_attrs(dynamic_values):
            value = attr.value
            # get value from db if exists
            if attr.persistent:
                persistent_keys.append(attr.key)
                dynamic_value_from_db = await collection.get_or_none(attr.key)
                if dynamic_value_from_db:
                    value = decode_value(dynamic_value_from_db.value)
            await cls.init_value(attr.key, value, attr.description, attr.persistent)

        # remove rows which not in persistent_keys
        await collection.delete_many({"_id": {"$nin": persistent_keys}})
        return cast(DYNAMIC_VALUES, cls.storage)

    @classmethod
    async def init_value(cls, key: str, value: object, description: str, persistent: bool) -> None:
        cls.persistent[key] = persistent
        cls.descriptions[key] = description
        cls.storage[key] = value
        if persistent:
            if not await cls.collection.exists({"_id": key}):
                await cls.collection.insert_one(DynamicValue(id=key, value=encode_value(value)))
            else:
                await cls.update_persistent_value(key, value)

    @classmethod
    async def update_value(cls, key: str, value: object) -> None:
        cls.storage[key] = value
        if cls.persistent[key]:
            await cls.update_persistent_value(key, value)

    @classmethod
    async def update_persistent_value(cls, key: str, value: object) -> None:
        await cls.collection.update(key, {"$set": {"value": encode_value(value), "updated_at": utc_now()}})


def encode_value(value: object) -> str:
    return base64.b64encode(pickle.dumps(value)).decode("utf-8")


def decode_value(value: str) -> object:
    return pickle.loads(base64.b64decode(value))  # noqa: S301 # nosec


def get_attrs(dynamic_values: type[DynamicValuesModel]) -> list[DV[Any]]:
    attrs: list[DV[Any]] = []
    keys = get_registered_public_attributes(dynamic_values)
    for key in keys:
        field = getattr(dynamic_values, key)
        if isinstance(field, DV):
            attrs.append(field)
    attrs.sort(key=lambda x: x.order)
    return attrs
