from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol, get_type_hints

from mm_concurrency import synchronized
from mm_concurrency.async_scheduler import AsyncScheduler
from mm_mongo import AsyncDatabaseAny, AsyncMongoConnection
from pymongo import AsyncMongoClient

from mm_base6.core.config import CoreConfig
from mm_base6.core.db import BaseDb
from mm_base6.core.logger import configure_logging
from mm_base6.core.services.event import EventService
from mm_base6.core.services.logfile import LogfileService
from mm_base6.core.services.settings import SettingsModel, SettingsService
from mm_base6.core.services.stat import StatService
from mm_base6.core.services.state import StateModel, StateService
from mm_base6.core.services.telegram import TelegramService

logger = logging.getLogger(__name__)


@dataclass
class BaseServices:
    """Container for framework's core services available to all applications.

    These services provide fundamental functionality needed by any application
    built with the framework: event logging, settings management, state persistence,
    statistics collection, log file operations, and Telegram integration.
    """

    event: EventService
    settings: SettingsService
    state: StateService
    stat: StatService
    logfile: LogfileService
    telegram: TelegramService


class CoreProtocol[SC: SettingsModel, ST: StateModel, DB: BaseDb, SR](Protocol):
    """Protocol defining the interface that all Core implementations must provide.

    Enables type-safe dependency injection in FastAPI routes and services.
    Generic parameters allow applications to define their own settings, state,
    database, and service registry types while maintaining type safety.
    """

    core_config: CoreConfig
    settings: SC
    state: ST
    db: DB
    services: SR
    base_services: BaseServices
    database: AsyncDatabaseAny
    scheduler: AsyncScheduler

    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def reinit_scheduler(self) -> None: ...


class Core[SC: SettingsModel, ST: StateModel, DB: BaseDb, SR]:
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
            core_config=CoreConfig(),
            settings_cls=MySettings,
            state_cls=MyState,
            db_cls=MyDb,
            service_registry_cls=MyServices,
        )
    """

    core_config: CoreConfig
    scheduler: AsyncScheduler
    mongo_client: AsyncMongoClient[Any]
    database: AsyncDatabaseAny
    db: DB
    settings: SC
    state: ST
    services: SR
    base_services: BaseServices

    def __new__(cls, *_args: object, **_kwargs: object) -> Core[SC, ST, DB, SR]:
        raise TypeError("Use `Core.init()` instead of direct instantiation.")

    @classmethod
    async def init(
        cls,
        core_config: CoreConfig,
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
            core_config: Framework configuration (database URL, data directory, etc.)
            settings_cls: Application settings model extending SettingsModel
            state_cls: Application state model extending StateModel
            db_cls: Database class extending BaseDb with application collections
            service_registry_cls: Class containing application-specific services

        Returns:
            Fully initialized Core instance ready for use

        Note:
            This method sets up logging, connects to MongoDB, initializes all
            framework services, loads persistent data, and injects dependencies.
        """
        configure_logging(core_config.debug, core_config.data_dir)
        inst = super().__new__(cls)
        inst.core_config = core_config
        inst.scheduler = AsyncScheduler()
        conn = AsyncMongoConnection(inst.core_config.database_url)
        inst.mongo_client = conn.client
        inst.database = conn.database
        inst.db = await db_cls.init_collections(conn.database)

        # base services
        event_service = EventService(inst.db)
        stat_service = StatService(inst.db, inst.scheduler)
        logfile_service = LogfileService(core_config)
        settings_service = SettingsService(event_service)
        state_service = StateService(event_service)
        telegram_service = TelegramService(event_service, settings_service)
        inst.base_services = BaseServices(
            event=event_service,
            settings=settings_service,
            state=state_service,
            stat=stat_service,
            logfile=logfile_service,
            telegram=telegram_service,
        )

        inst.settings = await settings_service.init_storage(inst.db.setting, settings_cls)
        inst.state = await state_service.init_storage(inst.db.state, state_cls)

        # Create and inject services
        inst.services = cls._create_services_from_registry_class(service_registry_cls)
        inst._inject_core_into_services()

        return inst

    def _inject_core_into_services(self) -> None:
        """Inject core instance into all user services extending Service."""
        for attr_name in dir(self.services):
            if not attr_name.startswith("_"):
                service = getattr(self.services, attr_name)
                if isinstance(service, Service):
                    service.set_core(self)

    async def _start_services(self) -> None:
        """Call on_start() for all user services."""
        for attr_name in dir(self.services):
            if not attr_name.startswith("_"):
                service = getattr(self.services, attr_name)
                if isinstance(service, Service):
                    await service.on_start()

    async def _stop_services(self) -> None:
        """Call on_stop() for all user services in reverse order."""
        services: list[Service[Any]] = []
        for attr_name in dir(self.services):
            if not attr_name.startswith("_"):
                service = getattr(self.services, attr_name)
                if isinstance(service, Service):
                    services.append(service)
        for service in reversed(services):
            await service.on_stop()

    def _configure_services_scheduler(self) -> None:
        """Call configure_scheduler() for all user services."""
        for attr_name in dir(self.services):
            if not attr_name.startswith("_"):
                service = getattr(self.services, attr_name)
                if isinstance(service, Service):
                    service.configure_scheduler()

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
        self._configure_services_scheduler()
        self.scheduler.start()

    async def startup(self) -> None:
        """Start the application with service initialization and scheduler.

        Calls on_start() for all services, initializes the task scheduler,
        and logs application start events.
        """
        await self._start_services()
        await self.reinit_scheduler()
        logger.info("app started")
        if not self.core_config.debug:
            await self.event("app_start")

    async def shutdown(self) -> None:
        """Shutdown the application with service cleanup.

        Calls on_stop() for all services, stops the scheduler,
        closes database connections, and logs shutdown events.
        """
        await self._stop_services()
        await self.scheduler.stop()
        if not self.core_config.debug:
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
        await self.base_services.event.event(event_type, data)

    @staticmethod
    def _create_services_from_registry_class(registry_cls: type[SR]) -> SR:
        """Create service instances from ServiceRegistry class using introspection.

        Automatically instantiates all services defined in the registry class
        type annotations. Each annotated field becomes a service instance,
        enabling declarative service registration without manual initialization.

        Args:
            registry_cls: Class with type annotations defining service types

        Returns:
            Registry instance with all services instantiated and ready for injection
        """

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


class Service[T]:
    """Base class for user services with lifecycle hooks.

    Generic parameter T is the Core type, allowing type-safe access
    to core without manual annotation in subclasses.

    Example:
        class MyService(Service[AppCore]):
            async def on_start(self) -> None:
                await self.core.db.my_collection.create_index("field")

            def configure_scheduler(self) -> None:
                self.core.scheduler.add_task("my_task", 60, self.my_task)

            async def on_stop(self) -> None:
                self._cache.clear()
    """

    _core: T | None = None

    def set_core(self, core: T) -> None:
        """Inject core reference (called during initialization)."""
        self._core = core

    @property
    def core(self) -> T:
        """Get the core application context."""
        if self._core is None:
            raise RuntimeError("Core not set for service")
        return self._core

    async def on_start(self) -> None:
        """Initialize service on application startup.

        Override to create database indexes, load caches, initialize connections.
        """

    async def on_stop(self) -> None:
        """Cleanup service on application shutdown.

        Override to close connections, flush caches, release resources.
        """

    def configure_scheduler(self) -> None:
        """Register scheduled tasks for this service.

        Called on startup and on scheduler reinit (when settings change).
        Override to add tasks via self.core.scheduler.add_task().
        """
