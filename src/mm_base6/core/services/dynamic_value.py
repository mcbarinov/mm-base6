from mm_std import toml_dumps, toml_loads
from pydantic import BaseModel

from mm_base6.core.dynamic_value import DynamicValueStorage
from mm_base6.core.errors import UserError
from mm_base6.core.services.system import SystemService


class DynamicValuesInfo(BaseModel):
    dynamic_values: dict[str, object]
    persistent: dict[str, bool]
    descriptions: dict[str, str]


class DynamicValueService:
    def __init__(self, system_service: SystemService) -> None:
        self.system_service = system_service

    def get_dynamic_values_info(self) -> DynamicValuesInfo:
        return DynamicValuesInfo(
            dynamic_values=DynamicValueStorage.storage,
            persistent=DynamicValueStorage.persistent,
            descriptions=DynamicValueStorage.descriptions,
        )

    def export_dynamic_values_as_toml(self) -> str:
        return toml_dumps(DynamicValueStorage.storage)

    def export_dynamic_value_as_toml(self, key: str) -> str:
        return toml_dumps({key: DynamicValueStorage.storage[key]})

    def get_dynamic_value(self, key: str) -> object:
        return DynamicValueStorage.storage[key]

    async def update_dynamic_value(self, key: str, toml_str: str) -> None:
        data = toml_loads(toml_str)
        if key not in data:
            raise UserError(f"Key '{key}' not found in toml data")
        await DynamicValueStorage.update_value(key, data[key])

    def has_dynamic_value_key(self, key: str) -> bool:
        return key in DynamicValueStorage.storage
