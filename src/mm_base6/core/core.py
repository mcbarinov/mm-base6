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
    - Application lifecycle hooks (startup/shutdown)
    - Event logging and monitoring integration

    Example:
        core = await Core.init(
            core_config=CoreConfig(),
            settings_cls=MySettings,
            state_cls=MyState,
            db_cls=MyDb,
            service_registry_cls=MyServices,
            lifespan_cls=MyLifecycle
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

    # User-provided lifecycle
    _lifecycle: CoreLifecycle[Core[SC, ST, DB, SR]] | None

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
        lifespan_cls: type[CoreLifecycle[Core[SC, ST, DB, SR]]] | None = None,
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
            lifespan_cls: Optional lifecycle handler for startup/shutdown hooks

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

        # Store user lifecycle class
        inst._lifecycle = lifespan_cls(inst) if lifespan_cls else None

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
        await inst._inject_core_into_services()

        return inst

    async def _inject_core_into_services(self) -> None:
        """Inject core instance into all user services extending Service.

        Enables services to access core functionality like event logging,
        settings, state, and other services through dependency injection.
        """
        for attr_name in dir(self.services):
            if not attr_name.startswith("_"):
                service = getattr(self.services, attr_name)
                if isinstance(service, Service):
                    service.core = self

    @synchronized
    async def reinit_scheduler(self) -> None:
        """Reinitialize the background task scheduler.

        Stops the current scheduler, clears all tasks, reconfigures tasks
        through the lifecycle handler, and restarts. Used for dynamic
        task management and scheduler updates during runtime.
        """
        logger.debug("Reinitializing scheduler...")
        if self.scheduler.is_running():
            await self.scheduler.stop()
        self.scheduler.clear_tasks()
        await self.configure_scheduler()
        self.scheduler.start()

    async def startup(self) -> None:
        """Start the application with lifecycle hooks and scheduler.

        Calls user-defined startup logic, initializes the task scheduler,
        and logs application start events. This is called automatically
        by the framework during application launch.
        """
        await self.start()
        await self.reinit_scheduler()
        logger.info("app started")
        if not self.core_config.debug:
            await self.event("app_start")

    async def shutdown(self) -> None:
        """Shutdown the application with cleanup and lifecycle hooks.

        Stops the scheduler, calls user-defined shutdown logic,
        closes database connections, and logs shutdown events.
        Performs a hard exit to ensure complete process termination.
        """
        await self.scheduler.stop()
        if not self.core_config.debug:
            await self.event("app_stop")
        await self.stop()
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

    async def configure_scheduler(self) -> None:
        """Call user-provided scheduler configuration through lifecycle handler.

        Delegates to the application's CoreLifecycle.configure_scheduler() method
        if a lifecycle handler was provided during initialization.
        """
        if self._lifecycle:
            await self._lifecycle.configure_scheduler()

    async def start(self) -> None:
        """Call user-provided startup logic through lifecycle handler.

        Delegates to the application's CoreLifecycle.on_startup() method
        if a lifecycle handler was provided during initialization.
        """
        if self._lifecycle:
            await self._lifecycle.on_startup()

    async def stop(self) -> None:
        """Call user-provided shutdown logic through lifecycle handler.

        Delegates to the application's CoreLifecycle.on_shutdown() method
        if a lifecycle handler was provided during initialization.
        """
        if self._lifecycle:
            await self._lifecycle.on_shutdown()

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


class Service:
    """Base class for user services. Core will be automatically injected."""

    core: Any  # Will be properly typed by user with type alias


class CoreLifecycle[T: "CoreProtocol[Any, Any, Any, Any]"]:
    """Base class for core lifecycle management.

    Provides hooks for scheduler configuration, startup, and shutdown logic.
    The core instance is available through self.core with proper typing.
    """

    def __init__(self, core: T) -> None:
        self.core = core

    async def configure_scheduler(self) -> None:
        """Configure background scheduler tasks."""

    async def on_startup(self) -> None:
        """Core startup logic."""

    async def on_shutdown(self) -> None:
        """Core shutdown logic."""
