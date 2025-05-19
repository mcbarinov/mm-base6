import pydash
from mm_std import toml_dumps, toml_loads
from pydantic import BaseModel

from mm_base6.core.db import DynamicConfigType
from mm_base6.core.dynamic_config import DynamicConfigStorage
from mm_base6.core.services.system import SystemService


class DynamicConfigsInfo(BaseModel):
    dynamic_configs: dict[str, object]
    descriptions: dict[str, str]
    types: dict[str, DynamicConfigType]
    hidden: set[str]


class DynamicConfigService:
    def __init__(self, system_service: SystemService) -> None:
        self.system_service = system_service

    def get_dynamic_configs_info(self) -> DynamicConfigsInfo:
        return DynamicConfigsInfo(
            dynamic_configs=DynamicConfigStorage.storage,
            descriptions=DynamicConfigStorage.descriptions,
            types=DynamicConfigStorage.types,
            hidden=DynamicConfigStorage.hidden,
        )

    def export_as_toml(self) -> str:
        result = pydash.omit(DynamicConfigStorage.storage, *DynamicConfigStorage.hidden)
        return toml_dumps(result)

    async def update_from_toml(self, toml_value: str) -> bool | None:
        data = toml_loads(toml_value)
        if isinstance(data, dict):
            return await DynamicConfigStorage.update({key: str(value) for key, value in data.items()})

    async def update_configs(self, data: dict[str, str]) -> bool:
        return await DynamicConfigStorage.update(data)

    def has_key(self, key: str) -> bool:
        return key in DynamicConfigStorage.storage
