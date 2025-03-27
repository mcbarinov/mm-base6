from __future__ import annotations

from app.core.db import Db
from app.core.services.data_service import DataService
from app.core.services.misc_service import MiscService
from app.settings import DConfigSettings, DValueSettings
from mm_base6 import BaseCore, CoreConfig


class Core(BaseCore[DConfigSettings, DValueSettings, Db]):
    data_service: DataService
    misc_service: MiscService

    @classmethod
    async def init(cls, core_config: CoreConfig) -> Core:
        res = await super().base_init(core_config, DConfigSettings, DValueSettings, Db)
        res.data_service = DataService(res.base_service_params)
        res.misc_service = MiscService(res.base_service_params)
        res.scheduler.add_task("data_service:generate_one", 60, res.data_service.generate_one)
        return res
