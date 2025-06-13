from typing import Self

from app.core.db import Db
from app.core.services.data import DataService
from app.core.services.misc import MiscService
from app.settings import DynamicConfigs, DynamicValues
from mm_base6 import BaseCore, CoreConfig


class ServiceRegistry:
    data: DataService
    misc: MiscService


class Core(BaseCore[DynamicConfigs, DynamicValues, Db, ServiceRegistry]):
    @classmethod
    async def init(cls, core_config: CoreConfig) -> Self:
        res = await super().base_init(core_config, DynamicConfigs, DynamicValues, Db, ServiceRegistry)
        res.services.data = DataService(res)
        res.services.misc = MiscService(res)

        return res

    async def configure_scheduler(self) -> None:
        self.scheduler.add_task("generate_one", 60, self.services.data.generate_one)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
