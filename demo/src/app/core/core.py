from typing import Self

from mm_base6 import BaseCore, CoreConfig

from app.core.db import Db
from app.core.services.data_service import DataService
from app.core.services.misc_service import MiscService
from app.settings import DynamicConfigs, DynamicValues


class ServiceRegistry:
    data_service: DataService
    misc_service: MiscService


class Core(BaseCore[DynamicConfigs, DynamicValues, Db, ServiceRegistry]):
    data_service: DataService
    misc_service: MiscService

    @classmethod
    async def init(cls, core_config: CoreConfig) -> Self:
        res = await super().base_init(core_config, DynamicConfigs, DynamicValues, Db, ServiceRegistry)
        res.data_service = DataService(res.base_service_params)
        res.misc_service = MiscService(res.base_service_params)
        res.services = ServiceRegistry()
        res.services.data_service = res.data_service
        res.services.misc_service = res.misc_service
        return res

    async def configure_scheduler(self) -> None:
        self.scheduler.add_task("generate_one", 60, self.data_service.generate_one)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
