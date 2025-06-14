from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from bson import ObjectId
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


class CoreProtocol[DC: DynamicConfigsModel, DV: DynamicValuesModel, DB: BaseDb, SR](Protocol):
    core_config: CoreConfig
    dynamic_configs: DC
    dynamic_values: DV
    db: DB
    services: SR
    base_services: BaseServices
    database: AsyncDatabaseAny
    scheduler: AsyncScheduler

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def reinit_scheduler(self) -> None: ...


class Core[DC: DynamicConfigsModel, DV: DynamicValuesModel, DB: BaseDb, SR]:
    core_config: CoreConfig
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB
    dynamic_configs: DC
    dynamic_values: DV
    services: SR
    base_services: BaseServices

    # User-provided functions
    _configure_scheduler_fn: Callable[[Core[DC, DV, DB, SR]], Awaitable[None]] | None
    _start_core_fn: Callable[[Core[DC, DV, DB, SR]], Awaitable[None]] | None
    _stop_core_fn: Callable[[Core[DC, DV, DB, SR]], Awaitable[None]] | None

    def __new__(cls, *_args: object, **_kwargs: object) -> Core[DC, DV, DB, SR]:
        raise TypeError("Use `Core.init()` instead of direct instantiation.")

    @classmethod
    async def init(
        cls,
        core_config: CoreConfig,
        dynamic_configs_cls: type[DC],
        dynamic_values_cls: type[DV],
        db_cls: type[DB],
        service_registry_cls: type[SR],
        configure_scheduler_fn: Callable[[Core[DC, DV, DB, SR]], Awaitable[None]] | None = None,
        start_core_fn: Callable[[Core[DC, DV, DB, SR]], Awaitable[None]] | None = None,
        stop_core_fn: Callable[[Core[DC, DV, DB, SR]], Awaitable[None]] | None = None,
    ) -> Core[DC, DV, DB, SR]:
        configure_logging(core_config.debug, core_config.data_dir)
        inst = super().__new__(cls)
        inst.core_config = core_config
        inst.scheduler = AsyncScheduler()
        conn = AsyncMongoConnection(inst.core_config.database_url)
        inst.mongo_client = conn.client
        inst.database = conn.database
        inst.db = await db_cls.init_collections(conn.database)

        # Store user functions
        inst._configure_scheduler_fn = configure_scheduler_fn
        inst._start_core_fn = start_core_fn
        inst._stop_core_fn = stop_core_fn

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

        # Create and inject services
        inst.services = cls._create_services_from_registry_class(service_registry_cls)
        await inst._inject_core_into_services()

        return inst

    async def _inject_core_into_services(self) -> None:
        """Inject core into all user services."""
        for attr_name in dir(self.services):
            if not attr_name.startswith("_"):
                service = getattr(self.services, attr_name)
                if isinstance(service, BaseService):
                    service.core = self

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

    async def configure_scheduler(self) -> None:
        """Call user-provided scheduler configuration function."""
        if self._configure_scheduler_fn:
            await self._configure_scheduler_fn(self)

    async def start(self) -> None:
        """Call user-provided start function."""
        if self._start_core_fn:
            await self._start_core_fn(self)

    async def stop(self) -> None:
        """Call user-provided stop function."""
        if self._stop_core_fn:
            await self._stop_core_fn(self)

    @staticmethod
    def _create_services_from_registry_class(registry_cls: type[SR]) -> SR:
        """Automatically create service instances from ServiceRegistry class annotations."""
        from typing import get_type_hints

        registry = registry_cls()

        # Get type annotations from the class, resolving string annotations safely
        try:
            annotations = get_type_hints(registry_cls)
        except (NameError, AttributeError):
            # Fallback to raw annotations if type hints can't be resolved
            annotations = getattr(registry_cls, "__annotations__", {})

        for attr_name, service_type_hint in annotations.items():
            # Create service instance
            service_instance = service_type_hint()
            setattr(registry, attr_name, service_instance)

        return registry


class BaseService:
    """Base class for user services. Core will be automatically injected."""

    core: Any  # Will be properly typed by user with type alias

    async def system_log(self, category: str, data: object = None) -> None:
        await self.core.base_services.system.system_log(category, data)

    async def send_telegram_message(self, message: str) -> object:
        return await self.core.base_services.telegram.send_message(message)
