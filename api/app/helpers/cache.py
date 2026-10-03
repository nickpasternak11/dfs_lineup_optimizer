import threading
import time
from typing import Any, Callable, Hashable


class TTLCache:
    """Process-wide cache whose entries expire `ttl` seconds after loading.

    Handlers run in FastAPI's thread pool, so access is locked. Loads are
    single-flight per key: when an entry is missing or stale, one thread runs
    the loader and the others asking for the same key wait for its result
    instead of all querying the database at once. Different keys load in
    parallel.

    Values are shared between requests, so callers must not mutate them;
    pass `copy` to hand each caller its own copy instead.
    """

    def __init__(
        self,
        ttl: float,
        copy: Callable[[Any], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.ttl = ttl
        self._copy = copy
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[Hashable, tuple[float, Any]] = {}
        self._key_locks: dict[Hashable, threading.Lock] = {}

    def get_or_load(self, key: Hashable, loader: Callable[[], Any]) -> Any:
        if self.ttl <= 0:
            return loader()

        value = self._fresh(key)
        if value is _MISSING:
            with self._lock:
                key_lock = self._key_locks.setdefault(key, threading.Lock())
            with key_lock:
                # Another thread may have loaded it while this one waited.
                value = self._fresh(key)
                if value is _MISSING:
                    value = loader()
                    with self._lock:
                        self._entries[key] = (self._clock() + self.ttl, value)
        return self._copy(value) if self._copy else value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _fresh(self, key: Hashable) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return _MISSING
            expires_at, value = entry
            if self._clock() >= expires_at:
                del self._entries[key]
                return _MISSING
            return value


_MISSING = object()
