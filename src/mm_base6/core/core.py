from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Generic, Self, TypeVar

from bson import ObjectId
from mm_mongo import AsyncDatabaseAny, AsyncMongoConnection
from mm_std import AsyncScheduler, Result, synchronized
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
from mm_base6.core.types import SERVICE_REGISTRY, SYSTEM_LOG

DYNAMIC_CONFIGS_co = TypeVar("DYNAMIC_CONFIGS_co", bound=DynamicConfigsModel, covariant=True)
DYNAMIC_VALUES_co = TypeVar("DYNAMIC_VALUES_co", bound=DynamicValuesModel, covariant=True)
DB_co = TypeVar("DB_co", bound=BaseDb, covariant=True)


DYNAMIC_CONFIGS = TypeVar("DYNAMIC_CONFIGS", bound=DynamicConfigsModel)
DYNAMIC_VALUES = TypeVar("DYNAMIC_VALUES", bound=DynamicValuesModel)
DB = TypeVar("DB", bound=BaseDb)


logger = logging.getLogger(__name__)


@dataclass
class BaseServices:
    dynamic_config: DynamicConfigService
    dynamic_value: DynamicValueService
    proxy: ProxyService
    system: SystemService
    telegram: TelegramService


class BaseCore(Generic[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co, SERVICE_REGISTRY], ABC):
    core_config: CoreConfig
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB_co
    dynamic_configs: DYNAMIC_CONFIGS_co
    dynamic_values: DYNAMIC_VALUES_co
    services: SERVICE_REGISTRY
    base_services: BaseServices

    def __new__(
        cls, *_args: object, **_kwargs: object
    ) -> BaseCore[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co, SERVICE_REGISTRY]:
        raise TypeError("Use `BaseCore.init()` instead of direct instantiation.")

    @classmethod
    @abstractmethod
    async def init(cls, core_config: CoreConfig) -> Self:
        pass

    @classmethod
    async def base_init(
        cls,
        core_config: CoreConfig,
        dynamic_configs_cls: type[DYNAMIC_CONFIGS_co],
        dynamic_values_cls: type[DYNAMIC_VALUES_co],
        db_cls: type[DB_co],
        service_registry_cls: type[SERVICE_REGISTRY],
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
            self.scheduler.stop()
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
        self.scheduler.stop()
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

    @property
    def base_service_params(self) -> BaseServiceParams[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co]:
        return BaseServiceParams(
            core_config=self.core_config,
            dynamic_configs=self.dynamic_configs,
            dynamic_values=self.dynamic_values,
            db=self.db,
            system_log=self.system_log,
            send_telegram_message=self.base_services.telegram.send_message,
        )

    @abstractmethod
    async def configure_scheduler(self) -> None:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass


type BaseCoreAny = BaseCore[DynamicConfigsModel, DynamicValuesModel, BaseDb]


@dataclass
class BaseServiceParams(Generic[DYNAMIC_CONFIGS, DYNAMIC_VALUES, DB]):
    core_config: CoreConfig
    dynamic_configs: DYNAMIC_CONFIGS
    dynamic_values: DYNAMIC_VALUES
    db: DB
    system_log: SYSTEM_LOG
    send_telegram_message: Callable[[str], Coroutine[Any, Any, Result[list[int]]]]


class BaseService(Generic[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co]):
    def __init__(self, base_params: BaseServiceParams[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co]) -> None:
        self.core_config = base_params.core_config
        self.dynamic_configs: DYNAMIC_CONFIGS_co = base_params.dynamic_configs
        self.dynamic_values: DYNAMIC_VALUES_co = base_params.dynamic_values
        self.db = base_params.db
        self.system_log = base_params.system_log
        self.send_telegram_message = base_params.send_telegram_message
