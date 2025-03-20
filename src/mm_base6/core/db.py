from datetime import datetime
from enum import Enum, unique
from typing import Any, ClassVar, Self, get_args, get_origin, get_type_hints

from bson import ObjectId
from mm_mongo import AsyncDatabaseAny, AsyncMongoCollection, MongoModel
from mm_std import utc_now
from pydantic import BaseModel, ConfigDict, Field


@unique
class DConfigType(str, Enum):
    STRING = "STRING"
    MULTILINE = "MULTILINE"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    DECIMAL = "DECIMAL"


class DConfig(MongoModel[str]):
    type: DConfigType
    value: str
    updated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    __collection__: str = "dconfig"
    __validator__: ClassVar[dict[str, object]] = {
        "$jsonSchema": {
            "required": ["type", "value", "updated_at", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "string"},
                "type": {"enum": ["STRING", "MULTILINE", "DATETIME", "BOOLEAN", "INTEGER", "FLOAT", "DECIMAL"]},
                "value": {"bsonType": "string"},
                "updated_at": {"bsonType": ["date", "null"]},
                "created_at": {"bsonType": "date"},
            },
        },
    }


class DValue(MongoModel[str]):
    value: str
    updated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    __collection__: str = "dvalue"
    __validator__: ClassVar[dict[str, object]] = {
        "$jsonSchema": {
            "required": ["value", "updated_at", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "string"},
                "value": {"bsonType": "string"},
                "updated_at": {"bsonType": ["date", "null"]},
                "created_at": {"bsonType": "date"},
            },
        },
    }


class DLog(MongoModel[ObjectId]):
    category: str
    data: object
    created_at: datetime = Field(default_factory=utc_now)

    __collection__: str = "dlog"
    __indexes__ = "category, created_at"
    __validator__: ClassVar[dict[str, object]] = {
        "$jsonSchema": {
            "required": ["category", "data", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "category": {"bsonType": "string"},
                "data": {},
                "created_at": {"bsonType": "date"},
            },
        },
    }


class BaseDb(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    dlog: AsyncMongoCollection[ObjectId, DLog]
    dconfig: AsyncMongoCollection[str, DConfig]
    dvalue: AsyncMongoCollection[str, DValue]

    database: AsyncDatabaseAny

    @classmethod
    async def init_collections(cls, database: AsyncDatabaseAny) -> Self:
        data: dict[str, AsyncMongoCollection[Any, Any]] = {}
        for key, value in cls._mongo_collections().items():
            model = get_args(value)[1]
            data[key] = await AsyncMongoCollection.init(database, model)
        return cls(**data, database=database)

    @classmethod
    def _mongo_collections(cls) -> dict[str, AsyncMongoCollection[Any, Any]]:
        result: dict[str, AsyncMongoCollection[Any, Any]] = {}

        for base in reversed(cls.__mro__):
            # Try to get the fully resolved annotations first
            try:
                annotations = get_type_hints(base)
            except (NameError, TypeError):
                # Fall back to __annotations__ if the get_type_hints fails
                if hasattr(base, "__annotations__"):
                    annotations = base.__annotations__
                else:
                    continue

            for key, value in annotations.items():
                # Check if the annotation is a MongoCollection
                origin = get_origin(value)
                if origin is AsyncMongoCollection:
                    result[key] = value

        return result
