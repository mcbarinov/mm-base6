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
from mm_base6.core.system_service import SystemService
from mm_base6.core.types_ import SYSTEM_LOG

DYNAMIC_CONFIGS_co = TypeVar("DYNAMIC_CONFIGS_co", bound=DynamicConfigsModel, covariant=True)
DYNAMIC_VALUES_co = TypeVar("DYNAMIC_VALUES_co", bound=DynamicValuesModel, covariant=True)
DB_co = TypeVar("DB_co", bound=BaseDb, covariant=True)


DYNAMIC_CONFIGS = TypeVar("DYNAMIC_CONFIGS", bound=DynamicConfigsModel)
DYNAMIC_VALUES = TypeVar("DYNAMIC_VALUES", bound=DynamicValuesModel)
DB = TypeVar("DB", bound=BaseDb)


logger = logging.getLogger(__name__)


class BaseCore(Generic[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co], ABC):
    core_config: CoreConfig
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB_co
    dynamic_configs: DYNAMIC_CONFIGS_co
    dynamic_values: DYNAMIC_VALUES_co
    system_service: SystemService

    def __new__(cls, *_args: object, **_kwargs: object) -> BaseCore[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co]:
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
    ) -> Self:
        configure_logging(core_config.debug, core_config.data_dir)
        inst = super().__new__(cls)
        inst.core_config = core_config
        inst.scheduler = AsyncScheduler()
        conn = AsyncMongoConnection(inst.core_config.database_url)
        inst.mongo_client = conn.client
        inst.database = conn.database
        inst.db = await db_cls.init_collections(conn.database)

        inst.system_service = SystemService(core_config, inst.db, inst.scheduler)

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
        if self.system_service.has_proxies_settings():
            self.scheduler.add_task("system_update_proxies", 60, self.system_service.update_proxies)
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
            send_telegram_message=self.system_service.send_telegram_message,
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
