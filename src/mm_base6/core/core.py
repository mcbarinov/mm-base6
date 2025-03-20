from __future__ import annotations

import os
from abc import ABC
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from logging import Logger
from typing import Any, Generic, TypeVar

from bson import ObjectId
from mm_mongo import AsyncDatabaseAny, AsyncMongoConnection
from mm_std import AsyncScheduler, Err, Ok, init_logger
from pymongo import AsyncMongoClient

from mm_base6.core.config import CoreConfig
from mm_base6.core.db import BaseDb, DLog
from mm_base6.core.dconfig import DConfigModel, DConfigStorage
from mm_base6.core.dvalue import DValueModel, DValueStorage
from mm_base6.core.system_service import SystemService
from mm_base6.core.types_ import DLOG

DCONFIG_co = TypeVar("DCONFIG_co", bound=DConfigModel, covariant=True)
DVALUE_co = TypeVar("DVALUE_co", bound=DValueModel, covariant=True)
DB_co = TypeVar("DB_co", bound=BaseDb, covariant=True)


DCONFIG = TypeVar("DCONFIG", bound=DConfigModel)
DVALUE = TypeVar("DVALUE", bound=DValueModel)
DB = TypeVar("DB", bound=BaseDb)


class BaseCore(Generic[DCONFIG_co, DVALUE_co, DB_co], ABC):
    core_config: CoreConfig
    logger: Logger
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB_co
    dconfig: DCONFIG_co
    dvalue: DVALUE_co
    system_service: SystemService

    def __new__(cls, *_args: object, **_kwargs: object) -> BaseCore[DCONFIG_co, DVALUE_co, DB_co]:
        raise TypeError("Use `BaseCore.init()` instead of direct instantiation.")

    @classmethod
    async def base_init(
        cls,
        core_config: CoreConfig,
        dconfig_settings: type[DCONFIG_co],
        dvalue_settings: type[DVALUE_co],
        db_settings: type[DB_co],
    ) -> BaseCore[DCONFIG_co, DVALUE_co, DB_co]:
        inst = super().__new__(cls)
        inst.core_config = core_config
        inst.logger = init_logger("app", file_path=f"{core_config.data_dir}/app.log", level=core_config.logger_level)
        inst.scheduler = AsyncScheduler(inst.logger)
        conn = AsyncMongoConnection(inst.core_config.database_url)
        inst.mongo_client = conn.client
        inst.database = conn.database
        inst.db = await db_settings.init_collections(conn.database)

        inst.system_service = SystemService(core_config, inst.logger, inst.db, inst.scheduler)

        inst.dconfig = await DConfigStorage.init_storage(inst.db.dconfig, dconfig_settings, inst.dlog)
        inst.dvalue = await DValueStorage.init_storage(inst.db.dvalue, dvalue_settings)

        if inst.system_service.has_proxies_settings():
            inst.scheduler.add_task("system_update_proxies", 60, inst.system_service.update_proxies)

        return inst

    async def startup(self) -> None:
        self.scheduler.start()
        await self.start()
        self.logger.debug("app started")
        if not self.core_config.debug:
            await self.dlog("app_start")

    async def shutdown(self) -> None:
        self.scheduler.stop()
        if not self.core_config.debug:
            await self.dlog("app_stop")
        await self.stop()
        await self.mongo_client.close()
        self.logger.debug("app stopped")
        # noinspection PyUnresolvedReferences,PyProtectedMember
        os._exit(0)

    async def dlog(self, category: str, data: object = None) -> None:
        self.logger.debug("system_log %s %s", category, data)
        await self.db.dlog.insert_one(DLog(id=ObjectId(), category=category, data=data))

    @property
    def base_service_params(self) -> BaseServiceParams[DCONFIG_co, DVALUE_co, DB_co]:
        return BaseServiceParams(
            logger=self.logger,
            core_config=self.core_config,
            dconfig=self.dconfig,
            dvalue=self.dvalue,
            db=self.db,
            dlog=self.dlog,
            send_telegram_message=self.system_service.send_telegram_message,
        )

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


type BaseCoreAny = BaseCore[DConfigModel, DValueModel, BaseDb]


@dataclass
class BaseServiceParams(Generic[DCONFIG, DVALUE, DB]):
    core_config: CoreConfig
    dconfig: DCONFIG
    dvalue: DVALUE
    db: DB
    logger: Logger
    dlog: DLOG
    send_telegram_message: Callable[[str], Coroutine[Any, Any, Ok[list[int]] | Err]]


class BaseService(Generic[DCONFIG_co, DVALUE_co, DB_co]):
    def __init__(self, base_params: BaseServiceParams[DCONFIG_co, DVALUE_co, DB_co]) -> None:
        self.core_config = base_params.core_config
        self.dconfig: DCONFIG_co = base_params.dconfig
        self.dvalue: DVALUE_co = base_params.dvalue
        self.db = base_params.db
        self.logger = base_params.logger
        self.dlog = base_params.dlog
        self.send_telegram_message = base_params.send_telegram_message
