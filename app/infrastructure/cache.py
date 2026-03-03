import time
from typing import Any


class TTLCache:

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._data: Any = None
        self._timestamp: float = 0.0

    def get(self) -> Any | None:
        if self._data is not None and (time.monotonic() - self._timestamp) < self._ttl:
            return self._data
        return None

    def set(self, data: Any) -> None:
        self._data = data
        self._timestamp = time.monotonic()

    def invalidate(self) -> None:
        self._data = None
        self._timestamp = 0.0


files_cache = TTLCache(ttl=60)
devices_cache = TTLCache(ttl=30)
