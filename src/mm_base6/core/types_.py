from collections.abc import Callable, Coroutine
from typing import Any

DLOG = Callable[[str, object], Coroutine[Any, Any, None]]
