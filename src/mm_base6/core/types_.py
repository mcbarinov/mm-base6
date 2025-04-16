from collections.abc import Callable, Coroutine
from typing import Any

SYSTEM_LOG = Callable[[str, object], Coroutine[Any, Any, None]]
