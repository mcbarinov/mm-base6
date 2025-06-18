from datetime import datetime
from enum import Enum, unique
from typing import Any, ClassVar, Self, get_args, get_origin, get_type_hints

from bson import ObjectId
from mm_mongo import AsyncDatabaseAny, AsyncMongoCollection, MongoModel
from mm_std import utc_now
from pydantic import BaseModel, ConfigDict, Field


@unique
class SettingType(str, Enum):
    """Database storage types for application settings values.

    Defines how settings values are stored as strings in MongoDB
    and converted back to Python types when retrieved.
    """

    STRING = "STRING"
    MULTILINE = "MULTILINE"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    DECIMAL = "DECIMAL"


class Setting(MongoModel[str]):
    """MongoDB document for storing application settings with type information.

    Settings are stored as strings in the database with type metadata
    to enable proper conversion back to Python types. Used by SettingsService
    to persist SettingsModel fields with validation and type safety.
    """

    type: SettingType
    value: str
    updated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    __collection__: str = "setting"
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


class State(MongoModel[str]):
    """MongoDB document for storing application state values.

    State values are serialized (pickled and base64-encoded) for storage
    and automatically restored when loaded. Used by StateService to persist
    StateModel fields that are marked as persistent=True.
    """

    value: str
    updated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    __collection__: str = "state"
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


class Event(MongoModel[ObjectId]):
    """MongoDB document for application event logging and monitoring.

    Events are used throughout the framework to track application behavior,
    errors, and state changes. The data field can contain any JSON-serializable
    object for flexible event payloads.
    """

    type: str
    data: object
    created_at: datetime = Field(default_factory=utc_now)

    __collection__: str = "event"
    __indexes__ = ["type", "created_at"]
    __validator__: ClassVar[dict[str, object]] = {
        "$jsonSchema": {
            "required": ["type", "data", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "type": {"bsonType": "string"},
                "data": {},
                "created_at": {"bsonType": "date"},
            },
        },
    }


class BaseDb(BaseModel):
    """Base database class providing core MongoDB collections for the framework.

    Automatically discovers and initializes all AsyncMongoCollection fields
    in derived classes using introspection. Provides the foundational collections
    needed by the framework's core services: settings, state, and event logging.

    Example:
        class Db(BaseDb):
            user: AsyncMongoCollection[ObjectId, User]
            product: AsyncMongoCollection[str, Product]
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    event: AsyncMongoCollection[ObjectId, Event]
    setting: AsyncMongoCollection[str, Setting]
    state: AsyncMongoCollection[str, State]

    database: AsyncDatabaseAny

    @classmethod
    async def init_collections(cls, database: AsyncDatabaseAny) -> Self:
        """Initialize all MongoDB collections defined in the class annotations.

        Automatically discovers AsyncMongoCollection fields and initializes them
        with the corresponding MongoModel classes, creating indexes and validators.

        Args:
            database: MongoDB database instance to create collections in

        Returns:
            Initialized database instance with all collections ready for use
        """
        data: dict[str, AsyncMongoCollection[Any, Any]] = {}
        for key, value in cls._mongo_collections().items():
            model = get_args(value)[1]
            data[key] = await AsyncMongoCollection.init(database, model)
        return cls(**data, database=database)

    @classmethod
    def _mongo_collections(cls) -> dict[str, AsyncMongoCollection[Any, Any]]:
        """Discover AsyncMongoCollection fields in the class hierarchy.

        Uses introspection to find all fields typed as AsyncMongoCollection
        across the entire class hierarchy, enabling automatic collection
        initialization without manual registration.

        Returns:
            Dictionary mapping field names to their AsyncMongoCollection types
        """
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
