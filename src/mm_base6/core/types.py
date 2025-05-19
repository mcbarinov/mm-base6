from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

SERVICE_REGISTRY = TypeVar("SERVICE_REGISTRY")
SYSTEM_LOG = Callable[[str, object], Coroutine[Any, Any, None]]
