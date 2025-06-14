from __future__ import annotations

from decimal import Decimal
from typing import Any

import pydash
from mm_concurrency import synchronized
from mm_mongo import AsyncMongoCollection
from mm_result import Result
from mm_std import utc_now
from pydantic import BaseModel, ConfigDict, Field

from mm_base6.core.db import Setting, SettingType
from mm_base6.core.services.event import EventService
from mm_base6.core.utils import toml_dumps, toml_loads


def setting_field[T](default: T, description: str = "", hide: bool = False) -> T:
    """Create a settings field with metadata for SettingsModel."""
    return Field(default=default, description=description, json_schema_extra={"hide": hide})


class SettingsModel(BaseModel):
    """Base class for application settings with Pydantic validation."""

    model_config = ConfigDict(
        validate_assignment=True,  # Validate when setting attributes
        frozen=False,  # Allow attribute modification
        extra="forbid",  # Disallow extra attributes
    )


def _get_type(value: object) -> SettingType:
    """Determine the database storage type for a Python value."""
    if isinstance(value, bool):
        return SettingType.BOOLEAN
    if isinstance(value, str):
        return SettingType.MULTILINE if "\n" in value else SettingType.STRING
    if isinstance(value, Decimal):
        return SettingType.DECIMAL
    if isinstance(value, int):
        return SettingType.INTEGER
    if isinstance(value, float):
        return SettingType.FLOAT
    raise ValueError(f"unsupported type: {type(value)}")


def _get_typed_value(type_: SettingType, str_value: str) -> Result[Any]:
    """Convert string value from database to proper Python type."""
    try:
        if type_ == SettingType.BOOLEAN:
            return Result.ok(str_value.lower() == "true")
        if type_ == SettingType.INTEGER:
            return Result.ok(int(str_value))
        if type_ == SettingType.FLOAT:
            return Result.ok(float(str_value))
        if type_ == SettingType.DECIMAL:
            return Result.ok(Decimal(str_value))
        if type_ == SettingType.STRING:
            return Result.ok(str_value)
        if type_ == SettingType.MULTILINE:
            return Result.ok(str_value.replace("\r", ""))
        return Result.err(f"unsupported type: {type_}")
    except Exception as e:
        return Result.err(e)


class SettingsInfo(BaseModel):
    settings: dict[str, object]
    descriptions: dict[str, str]
    types: dict[str, SettingType]
    hidden: set[str]


class SettingsService:
    """Service for managing application settings with database persistence.

    Automatically synchronizes SettingsModel fields with MongoDB storage,
    handling type conversion and validation. Settings are stored as strings
    with type metadata for proper Python type restoration. Provides live
    updates with automatic database persistence when settings change.
    """

    def __init__(self, event_service: EventService) -> None:
        self.event_service = event_service
        self.storage: SettingsModel | None = None
        self.collection: AsyncMongoCollection[str, Setting] | None = None

    @synchronized
    async def init_storage[SETTINGS: SettingsModel](
        self,
        collection: AsyncMongoCollection[str, Setting],
        settings_class: type[SETTINGS],
    ) -> SETTINGS:
        """Initialize settings storage from database with type-safe defaults.

        Loads existing settings from MongoDB, creates missing ones with defaults,
        and removes obsolete settings. Ensures database schema matches the
        current SettingsModel definition.

        Args:
            collection: MongoDB collection for storing settings
            settings_class: Pydantic model class defining the settings schema

        Returns:
            Initialized and validated settings instance
        """
        self.collection = collection

        # Get field schema from Pydantic model
        model_fields = settings_class.model_fields
        db_values: dict[str, Any] = {}

        for field_name, field_info in model_fields.items():
            # Check if field exists in database
            db_record = await collection.get_or_none(field_name)

            if db_record:
                # Use value from database
                typed_value_res = _get_typed_value(db_record.type, db_record.value)
                if typed_value_res.is_ok():
                    db_values[field_name] = typed_value_res.unwrap()
                else:
                    await self.event_service.event(
                        "settings.get_typed_value", {"error": typed_value_res.unwrap_err(), "field": field_name}
                    )
                    db_values[field_name] = field_info.default
            else:
                # Create database record with default value
                default_value = field_info.default
                type_ = _get_type(default_value)
                str_value = "True" if (type_ is SettingType.BOOLEAN and default_value) else str(default_value)
                await collection.insert_one(Setting(id=field_name, type=type_, value=str_value))
                db_values[field_name] = default_value

        # Remove database records that don't exist in current schema
        current_field_names = list(model_fields.keys())
        await collection.delete_many({"_id": {"$nin": current_field_names}})

        # Create and store the instance
        self.storage = settings_class.model_validate(db_values)
        return self.storage

    async def update(self, data: dict[str, str]) -> bool:
        """Update configuration values from form data."""
        if not self.storage or not self.collection:
            return False

        result = True
        model_fields = self.storage.model_fields

        for key, value in data.items():
            if key in model_fields:
                field_info = model_fields[key]
                clean_value = value.replace("\r", "")  # Clean textarea input

                # Get expected type from field annotation
                expected_type = _get_type(field_info.default)
                type_value_res = _get_typed_value(expected_type, clean_value.strip())

                if type_value_res.is_ok():
                    # Update database
                    await self.collection.set(key, {"value": clean_value, "updated_at": utc_now()})
                    # Update instance
                    setattr(self.storage, key, type_value_res.unwrap())
                else:
                    await self.event_service.event(
                        "DynamicConfigStorage.update", {"error": type_value_res.unwrap_err(), "key": key}
                    )
                    result = False
            else:
                await self.event_service.event("DynamicConfigStorage.update", {"error": "unknown key", "key": key})
                result = False
        return result

    def _is_field_hidden(self, field_info: object) -> bool:
        """Check if a field is marked as hidden."""
        json_schema_extra = getattr(field_info, "json_schema_extra", {})
        return isinstance(json_schema_extra, dict) and json_schema_extra.get("hide", False)

    def get_visible_keys(self) -> set[str]:
        """Get field names that are not marked as hidden."""
        if not self.storage:
            return set()
        return {
            field_name for field_name, field_info in self.storage.model_fields.items() if not self._is_field_hidden(field_info)
        }

    def get_hidden_keys(self) -> set[str]:
        """Get field names that are marked as hidden."""
        if not self.storage:
            return set()
        return {field_name for field_name, field_info in self.storage.model_fields.items() if self._is_field_hidden(field_info)}

    def get_type(self, key: str) -> SettingType:
        """Get the database storage type for a specific field."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        field_info = self.storage.model_fields[key]
        return _get_type(field_info.default)

    def get_settings_info(self) -> SettingsInfo:
        """Get comprehensive information about all settings including types and visibility."""
        if not self.storage:
            raise ValueError("Storage not initialized")

        # Extract descriptions from field info
        descriptions = {}
        types = {}
        for field_name, field_info in self.storage.model_fields.items():
            descriptions[field_name] = field_info.description or ""
            types[field_name] = self.get_type(field_name)

        return SettingsInfo(
            settings=self.storage.model_dump(),
            descriptions=descriptions,
            types=types,
            hidden=self.get_hidden_keys(),
        )

    def export_as_toml(self) -> str:
        """Export non-hidden settings as TOML string."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        storage_dict = self.storage.model_dump()
        hidden_keys = self.get_hidden_keys()
        result = pydash.omit(storage_dict, *hidden_keys)
        return toml_dumps(result)

    async def update_from_toml(self, toml_value: str) -> bool | None:
        """Update settings from TOML string. Returns None if TOML is invalid."""
        data = toml_loads(toml_value)
        if isinstance(data, dict):
            return await self.update({key: str(value) for key, value in data.items()})
        return None

    async def update_configs(self, data: dict[str, str]) -> bool:
        """Update settings from dictionary of string values. Alias for update()."""
        return await self.update(data)

    def get_setting(self, key: str) -> object:
        """Get a setting value by key."""
        if not self.storage:
            raise ValueError("Storage not initialized")
        return getattr(self.storage, key)

    def has_setting(self, key: str) -> bool:
        """Check if a setting exists."""
        if not self.storage:
            return False
        return hasattr(self.storage, key)
