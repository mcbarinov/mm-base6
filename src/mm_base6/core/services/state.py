from __future__ import annotations

import asyncio
import base64
import pickle  # nosec: B403

from mm_concurrency import synchronized
from mm_mongo import AsyncMongoCollection
from mm_std import utc_now
from pydantic import BaseModel, Field

from mm_base6.core.db import State
from mm_base6.core.errors import UnregisteredStateError, UserError
from mm_base6.core.services.event import EventService
from mm_base6.core.utils import toml_dumps, toml_loads


def state_field[T](default: T, description: str = "", persistent: bool = True) -> T:
    """Create a state field with metadata for StateModel."""
    return Field(default=default, description=description, json_schema_extra={"persistent": persistent})


class StateModel(BaseModel):
    """Base class for state management using Pydantic."""

    model_config = {"extra": "forbid", "arbitrary_types_allowed": True}


class StateInfo(BaseModel):
    """Information about state configuration including values, persistence, and descriptions."""

    state: dict[str, object]
    persistent: dict[str, bool]
    descriptions: dict[str, str]


class StateService:
    """Service for managing application state with MongoDB persistence.

    Handles StateModel fields with automatic serialization/deserialization using pickle.
    Supports both persistent (saved to DB) and transient (memory-only) state fields.
    Provides automatic database synchronization when persistent state values change.
    """

    def __init__(self, event_service: EventService) -> None:
        self.event_service = event_service
        self.storage: StateModel | None = None
        self.collection: AsyncMongoCollection[str, State] | None = None
        self.persistent: dict[str, bool] = {}
        self.descriptions: dict[str, str] = {}

    @synchronized
    async def init_storage[STATE: StateModel](
        self,
        collection: AsyncMongoCollection[str, State],
        state_class: type[STATE],
    ) -> STATE:
        """Initialize state storage with automatic persistence management.

        Loads persistent state from MongoDB, creates missing entries with defaults,
        and sets up automatic saving for fields marked as persistent=True.
        Non-persistent fields remain in memory only.

        Args:
            collection: MongoDB collection for storing persistent state
            state_class: Pydantic model class defining the state schema

        Returns:
            Initialized state instance with persistent fields loaded from database
        """
        self.collection = collection

        # Extract field metadata
        model_fields = state_class.model_fields
        db_values: dict[str, object] = {}
        persistent_keys = []

        for field_name, field_info in model_fields.items():
            # Extract metadata from field
            persistent = True
            description = field_info.description or ""

            if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                persistent = bool(field_info.json_schema_extra.get("persistent", True))

            self.persistent[field_name] = persistent
            self.descriptions[field_name] = description

            if persistent:
                persistent_keys.append(field_name)
                # Try to load from database
                db_record = await collection.get_or_none(field_name)
                if db_record:
                    try:
                        db_values[field_name] = self._decode_value(db_record.value)
                    except Exception as e:
                        await self.event_service.event("state.decode_value", {"error": str(e), "field": field_name})
                        db_values[field_name] = field_info.default
                else:
                    # Create database record with default value
                    default_value = field_info.default
                    db_values[field_name] = default_value
                    await collection.insert_one(State(id=field_name, value=self._encode_value(default_value)))
            else:
                # Non-persistent fields use default values
                db_values[field_name] = field_info.default

        # Remove old entries from database
        await collection.delete_many({"_id": {"$nin": persistent_keys}})

        # Create model instance with values
        self.storage = state_class.model_validate(db_values)

        # Set up auto-save for persistent fields
        self._setup_autosave()

        return self.storage

    def _setup_autosave(self) -> None:
        """Setup automatic saving for persistent fields.

        This intercepts attribute assignments (e.g., core.state.field = value) and
        automatically saves persistent fields to the database. This allows users to
        modify state synchronously while handling async database operations behind the scenes.

        The complexity is necessary to maintain a simple user API where
        `core.state.my_field = new_value` automatically persists to database
        without requiring explicit async calls.
        """
        if not self.storage:
            return

        original_setattr = self.storage.__setattr__

        def autosave_setattr(name: str, value: object) -> None:
            original_setattr(name, value)
            if self.persistent.get(name, False):
                task = asyncio.create_task(self._update_persistent_value(name, value))
                # Store reference to prevent garbage collection
                task.add_done_callback(lambda _: None)

        # Use type: ignore to suppress mypy warnings about method assignment
        self.storage.__setattr__ = autosave_setattr  # type: ignore[method-assign]

    async def update_value(self, key: str, value: object) -> None:
        """Update a state value."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        if not hasattr(self.storage, key):
            raise UnregisteredStateError(key)

        setattr(self.storage, key, value)

        if self.persistent[key]:
            await self._update_persistent_value(key, value)

    async def _update_persistent_value(self, key: str, value: object) -> None:
        """Update a persistent value in the database."""
        if not self.collection:
            return
        await self.collection.update(key, {"$set": {"value": self._encode_value(value), "updated_at": utc_now()}})

    def get_non_persistent_keys(self) -> set[str]:
        """Get keys of non-persistent fields."""
        return {key for key, is_persistent in self.persistent.items() if not is_persistent}

    def get_state_info(self) -> StateInfo:
        """Get comprehensive information about state including values, persistence, and descriptions."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        return StateInfo(
            state=self.storage.model_dump(),
            persistent=self.persistent,
            descriptions=self.descriptions,
        )

    def export_state_as_toml(self) -> str:
        """Export all state values as TOML string."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        return toml_dumps(self.storage.model_dump())

    def export_state_value_as_toml(self, key: str) -> str:
        """Export a single state value as TOML string."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        storage_dict = self.storage.model_dump()
        return toml_dumps({key: storage_dict[key]})

    def get_state_value(self, key: str) -> object:
        """Get a state value by key."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        return getattr(self.storage, key)

    def has_state_value(self, key: str) -> bool:
        """Check if a state value exists."""
        if not self.storage:
            return False
        return hasattr(self.storage, key)

    async def update_state_value(self, key: str, toml_str: str) -> None:
        """Update a state value from TOML string."""
        data = toml_loads(toml_str)
        if key not in data:
            raise UserError(f"Key '{key}' not found in toml data")
        await self.update_value(key, data[key])

    async def update_from_toml(self, toml_str: str) -> bool | None:
        """Update state from TOML string. Returns None if TOML is invalid."""
        data = toml_loads(toml_str)
        if isinstance(data, dict):
            for key, value in data.items():
                if self.has_state_value(key):
                    await self.update_value(key, value)
            return True
        return None

    def _encode_value(self, value: object) -> str:
        """Encode a Python value to base64 string using pickle."""
        return base64.b64encode(pickle.dumps(value)).decode("utf-8")

    def _decode_value(self, value: str) -> object:
        """Decode a base64 string to Python value using pickle."""
        return pickle.loads(base64.b64decode(value))  # noqa: S301 # nosec
