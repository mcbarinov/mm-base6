import threading

from app.core.types_ import AppService, AppServiceParams


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


class MiscService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)
        self.counter = ThreadSafeCounter()

    def increment_counter(self) -> int:
        self.counter.increment()
        return self.counter.get()

    async def update_dvalue(self) -> int:
        self.dvalue.processed_block = self.dvalue.processed_block + 1
        return self.dvalue.processed_block
