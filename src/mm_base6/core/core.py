from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from mm_concurrency import synchronized
from mm_concurrency.async_scheduler import AsyncScheduler
from mm_mongo import AsyncDatabaseAny, AsyncMongoConnection
from pymongo import AsyncMongoClient

from mm_base6.config import Config
from mm_base6.core.builtin_services import BuiltinServices
from mm_base6.core.builtin_services.settings import BaseSettings
from mm_base6.core.builtin_services.state import BaseState
from mm_base6.core.db import BaseDb
from mm_base6.core.logger import configure_logging
from mm_base6.core.service import create_services_from_registry, get_services

logger = logging.getLogger(__name__)


class CoreProtocol[SC: BaseSettings, ST: BaseState, DB: BaseDb, SR](Protocol):
    """Protocol defining the interface that all Core implementations must provide.

    Enables type-safe dependency injection in FastAPI routes and services.
    Generic parameters allow applications to define their own settings, state,
    database, and service registry types while maintaining type safety.
    """

    config: Config
    settings: SC
    state: ST
    db: DB
    services: SR
    builtin_services: BuiltinServices
    database: AsyncDatabaseAny
    scheduler: AsyncScheduler

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def reinit_scheduler(self) -> None: ...


class Core[SC: BaseSettings, ST: BaseState, DB: BaseDb, SR]:
    """Central application framework providing integrated services and lifecycle management.

    Core orchestrates all framework components: MongoDB collections, settings/state management,
    event logging, background scheduler, and user-defined services. It handles initialization,
    dependency injection, and graceful shutdown. Applications extend Core by providing their
    own typed settings, state, database collections, and service registries.

    Key responsibilities:
    - Database connection and collection initialization
    - Settings and state persistence with type safety
    - Background task scheduling and management
    - Service registration and dependency injection
    - Service lifecycle hooks (on_start/on_stop/configure_scheduler)
    - Event logging and monitoring integration

    Example:
        core = await Core.init(
            config=Config(),
            settings_cls=MySettings,
            state_cls=MyState,
            db_cls=MyDb,
            service_registry_cls=MyServices,
        )
    """

    config: Config
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB
    settings: SC
    state: ST
    services: SR
    builtin_services: BuiltinServices

    def __new__(cls, *_args: object, **_kwargs: object) -> Core[SC, ST, DB, SR]:
        raise TypeError("Use `Core.init()` instead of direct instantiation.")

    @classmethod
    async def init(
        cls,
        config: Config,
        settings_cls: type[SC],
        state_cls: type[ST],
        db_cls: type[DB],
        service_registry_cls: type[SR],
    ) -> Core[SC, ST, DB, SR]:
        """Initialize the Core with all services and dependencies.

        Creates a fully configured Core instance with MongoDB connection,
        initialized services, loaded settings/state, and user service registry.
        This is the primary entry point for application initialization.

        Args:
            config: Application configuration (database URL, data directory, HTTP settings, etc.)
            settings_cls: Application settings model extending BaseSettings
            state_cls: Application state model extending BaseState
            db_cls: Database class extending BaseDb with application collections
            service_registry_cls: Class containing application-specific services

        Returns:
            Fully initialized Core instance ready for use

        Note:
            This method sets up logging, connects to MongoDB, initializes all
            framework services, loads persistent data, and injects dependencies.
        """
        configure_logging(config.debug, config.data_dir)
        inst = super().__new__(cls)
        inst.config = config
        inst.scheduler = AsyncScheduler()
        conn = AsyncMongoConnection(inst.config.database_url)
        inst.mongo_client = conn.client
        inst.database = conn.database
        inst.db = await db_cls.init_collections(conn.database)

        inst.builtin_services = BuiltinServices.init(inst.db, inst.scheduler, config)

        inst.settings = await inst.builtin_services.settings.init_storage(inst.db.setting, settings_cls)
        inst.state = await inst.builtin_services.state.init_storage(inst.db.state, state_cls)

        # Create and inject core into user services
        inst.services = create_services_from_registry(service_registry_cls)
        for service in get_services(inst.services):
            service.set_core(inst)

        return inst

    @synchronized
    async def reinit_scheduler(self) -> None:
        """Reinitialize the background task scheduler.

        Stops the current scheduler, clears all tasks, reconfigures tasks
        through service configure_scheduler() methods, and restarts.
        """
        logger.debug("Reinitializing scheduler...")
        if self.scheduler.is_running():
            await self.scheduler.stop()
        self.scheduler.clear_tasks()
        # Register scheduled tasks from user services
        for service in get_services(self.services):
            service.configure_scheduler()
        self.scheduler.start()

    async def startup(self) -> None:
        """Start the application with service initialization and scheduler.

        Calls on_start() for all services, initializes the task scheduler,
        and logs application start events.
        """
        # Initialize user services
        for service in get_services(self.services):
            await service.on_start()
        await self.reinit_scheduler()
        logger.info("app started")
        if not self.config.debug:
            await self.event("app_start")

    async def shutdown(self) -> None:
        """Shutdown the application with service cleanup.

        Calls on_stop() for all services, stops the scheduler,
        closes database connections, and logs shutdown events.
        """
        # Stop user services in reverse order
        for service in reversed(get_services(self.services)):
            await service.on_stop()
        await self.scheduler.stop()
        if not self.config.debug:
            await self.event("app_stop")
        await self.mongo_client.close()
        logger.info("app stopped")
        # noinspection PyUnresolvedReferences,PyProtectedMember
        os._exit(0)

    async def event(self, event_type: str, data: object = None) -> None:
        """Log an application event through the event service.

        Convenience method providing direct access to event logging
        from the core. Events are persisted to MongoDB for monitoring.

        Args:
            event_type: Event category/type identifier
            data: Optional event payload data
        """
        logger.debug("event %s %s", event_type, data)
        await self.builtin_services.event.event(event_type, data)
