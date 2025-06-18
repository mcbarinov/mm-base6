import threading

from app.core.types import AppCore
from mm_base6 import Service


class ThreadSafeCounter:
    def __init__(self) -> None:
        self.value = 0
        self._lock = threading.Lock()

    def increment(self) -> None:
        with self._lock:
            self.value += 1

    def get(self) -> int:
        with self._lock:
            return self.value


class MiscService(Service):
    core: AppCore

    def __init__(self) -> None:
        self.counter = ThreadSafeCounter()

    def increment_counter(self) -> int:
        self.counter.increment()
        return self.counter.get()

    async def update_state_value(self) -> int:
        self.core.state.processed_block = self.core.state.processed_block + 1
        return self.core.state.processed_block
