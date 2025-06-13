from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, Self

from bson import ObjectId

if TYPE_CHECKING:
    pass
from mm_concurrency import synchronized
from mm_concurrency.async_scheduler import AsyncScheduler
from mm_mongo import AsyncDatabaseAny, AsyncMongoConnection
from pymongo import AsyncMongoClient

from mm_base6.core.config import CoreConfig
from mm_base6.core.db import BaseDb, SystemLog
from mm_base6.core.dynamic_config import DynamicConfigsModel, DynamicConfigStorage
from mm_base6.core.dynamic_value import DynamicValuesModel, DynamicValueStorage
from mm_base6.core.logger import configure_logging
from mm_base6.core.services.dynamic_config import DynamicConfigService
from mm_base6.core.services.dynamic_value import DynamicValueService
from mm_base6.core.services.proxy import ProxyService
from mm_base6.core.services.system import SystemService
from mm_base6.core.services.telegram import TelegramService

logger = logging.getLogger(__name__)


@dataclass
class BaseServices:
    dynamic_config: DynamicConfigService
    dynamic_value: DynamicValueService
    proxy: ProxyService
    system: SystemService
    telegram: TelegramService


class CoreProtocol[DC: DynamicConfigsModel, DV: DynamicValuesModel, DB: BaseDb](Protocol):
    core_config: CoreConfig
    dynamic_configs: DC
    dynamic_values: DV
    db: DB
    base_services: BaseServices
    database: AsyncDatabaseAny
    scheduler: AsyncScheduler

    async def shutdown(self) -> None: ...
    async def reinit_scheduler(self) -> None: ...


class BaseCore[DC: DynamicConfigsModel, DV: DynamicValuesModel, DB: BaseDb, SR](ABC):
    core_config: CoreConfig
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB
    dynamic_configs: DC
    dynamic_values: DV
    services: SR
    base_services: BaseServices

    def __new__(cls, *_args: object, **_kwargs: object) -> BaseCore[DC, DV, DB, SR]:
        raise TypeError("Use `BaseCore.init()` instead of direct instantiation.")

    @classmethod
    @abstractmethod
    async def init(cls, core_config: CoreConfig) -> Self:
        pass

    @classmethod
    async def base_init(
        cls,
        core_config: CoreConfig,
        dynamic_configs_cls: type[DC],
        dynamic_values_cls: type[DV],
        db_cls: type[DB],
        service_registry_cls: type[SR],
    ) -> Self:
        configure_logging(core_config.debug, core_config.data_dir)
        inst = super().__new__(cls)
        inst.core_config = core_config
        inst.scheduler = AsyncScheduler()
        conn = AsyncMongoConnection(inst.core_config.database_url)
        inst.mongo_client = conn.client
        inst.database = conn.database
        inst.db = await db_cls.init_collections(conn.database)
        inst.services = service_registry_cls()

        # base services
        system_service = SystemService(core_config, inst.db, inst.scheduler)
        dynamic_config_service = DynamicConfigService(system_service)
        dynamic_value_service = DynamicValueService(system_service)
        proxy_service = ProxyService(system_service)
        telegram_service = TelegramService(system_service)
        inst.base_services = BaseServices(
            dynamic_config=dynamic_config_service,
            dynamic_value=dynamic_value_service,
            proxy=proxy_service,
            system=system_service,
            telegram=telegram_service,
        )

        inst.dynamic_configs = await DynamicConfigStorage.init_storage(
            inst.db.dynamic_config, dynamic_configs_cls, inst.system_log
        )
        inst.dynamic_values = await DynamicValueStorage.init_storage(inst.db.dynamic_value, dynamic_values_cls)

        return inst

    @synchronized
    async def reinit_scheduler(self) -> None:
        logger.debug("Reinitializing scheduler...")
        if self.scheduler.is_running():
            await self.scheduler.stop()
        self.scheduler.clear_tasks()
        if self.base_services.proxy.has_proxies_settings():
            self.scheduler.add_task("system_update_proxies", 60, self.base_services.proxy.update_proxies)
        await self.configure_scheduler()
        self.scheduler.start()

    async def startup(self) -> None:
        await self.start()
        await self.reinit_scheduler()
        logger.info("app started")
        if not self.core_config.debug:
            await self.system_log("app_start")

    async def shutdown(self) -> None:
        await self.scheduler.stop()
        if not self.core_config.debug:
            await self.system_log("app_stop")
        await self.stop()
        await self.mongo_client.close()
        logger.info("app stopped")
        # noinspection PyUnresolvedReferences,PyProtectedMember
        os._exit(0)

    async def system_log(self, category: str, data: object = None) -> None:
        logger.debug("system_log %s %s", category, data)
        await self.db.system_log.insert_one(SystemLog(id=ObjectId(), category=category, data=data))

    @abstractmethod
    async def configure_scheduler(self) -> None:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass


class BaseService[C]:
    def __init__(self, core: C) -> None:
        self.core = core

    # Convenience properties for common operations
    @property
    def core_config(self) -> CoreConfig:
        return self.core.core_config  # type: ignore[attr-defined,no-any-return]

    @property
    def dynamic_configs(self) -> object:
        return self.core.dynamic_configs  # type: ignore[attr-defined]

    @property
    def dynamic_values(self) -> object:
        return self.core.dynamic_values  # type: ignore[attr-defined]

    @property
    def db(self) -> object:
        return self.core.db  # type: ignore[attr-defined]

    async def system_log(self, category: str, data: object = None) -> None:
        await self.core.base_services.system.system_log(category, data)  # type: ignore[attr-defined]

    async def send_telegram_message(self, message: str) -> object:
        return await self.core.base_services.telegram.send_message(message)  # type: ignore[attr-defined]
