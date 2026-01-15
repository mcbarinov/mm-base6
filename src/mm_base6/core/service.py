from __future__ import annotations

from typing import Any, get_type_hints


class Service[T]:
    """Base class for user services with lifecycle hooks.

    Generic parameter T is the Core type, allowing type-safe access
    to core without manual annotation in subclasses.

    Example:
        from typing import override

        class MyService(Service[AppCore]):
            @override
            async def on_start(self) -> None:
                await self.core.db.my_collection.create_index("field")

            @override
            def configure_scheduler(self) -> None:
                self.core.scheduler.add_task("my_task", 60, self.my_task)

            @override
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


def create_services_from_registry[T](registry_cls: type[T]) -> T:
    """Create service instances from ServiceRegistry class using introspection.

    Automatically instantiates all services defined in the registry class
    type annotations. Each annotated field becomes a service instance,
    enabling declarative service registration without manual initialization.
    """
    registry = registry_cls()

    try:
        annotations = get_type_hints(registry_cls)
    except (NameError, AttributeError):
        annotations = getattr(registry_cls, "__annotations__", {})

    for attr_name, service_type_hint in annotations.items():
        service_instance = service_type_hint()
        setattr(registry, attr_name, service_instance)

    return registry


def get_services(registry: object) -> list[Service[Any]]:
    """Extract all Service instances from a service registry."""
    services: list[Service[Any]] = []
    for attr_name in dir(registry):
        if not attr_name.startswith("_"):
            attr = getattr(registry, attr_name)
            if isinstance(attr, Service):
                services.append(attr)
    return services
