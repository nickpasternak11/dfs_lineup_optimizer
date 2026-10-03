import threading
import time

import pandas as pd
import pytest

import app.db.optimize as optimize_module
import app.helpers.optimize as helpers_module
from app.db.optimize import DFSLineupOptimizer
from app.helpers.cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class CountingLoader:
    def __init__(self, value=None, delay: float = 0.0):
        self.calls = 0
        self.value = value
        self.delay = delay
        self._lock = threading.Lock()

    def __call__(self):
        with self._lock:
            self.calls += 1
        time.sleep(self.delay)
        return self.value if self.value is not None else self.calls


def test_entry_is_reused_until_ttl_expires():
    clock = FakeClock()
    cache = TTLCache(ttl=60, clock=clock)
    loader = CountingLoader()

    assert cache.get_or_load("key", loader) == 1
    clock.now = 59.9
    assert cache.get_or_load("key", loader) == 1
    clock.now = 60.0
    assert cache.get_or_load("key", loader) == 2
    assert loader.calls == 2


def test_keys_are_cached_separately():
    cache = TTLCache(ttl=60)
    assert cache.get_or_load((2025, 3), lambda: "week 3") == "week 3"
    assert cache.get_or_load((2025, 4), lambda: "week 4") == "week 4"
    assert cache.get_or_load((2025, 3), lambda: "reloaded") == "week 3"


def test_zero_ttl_disables_caching():
    cache = TTLCache(ttl=0)
    loader = CountingLoader()
    cache.get_or_load("key", loader)
    cache.get_or_load("key", loader)
    assert loader.calls == 2


def test_failed_load_is_not_cached():
    cache = TTLCache(ttl=60)

    def failing():
        raise RuntimeError("database down")

    with pytest.raises(RuntimeError):
        cache.get_or_load("key", failing)
    assert cache.get_or_load("key", lambda: "recovered") == "recovered"


def test_concurrent_misses_load_once():
    # Requests arriving together for a cold week must share one query.
    cache = TTLCache(ttl=60)
    loader = CountingLoader(value="pool", delay=0.05)
    results = []
    start = threading.Barrier(16)

    def worker():
        start.wait()
        results.append(cache.get_or_load((2025, 3), loader))

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert loader.calls == 1
    assert results == ["pool"] * 16


def test_copy_keeps_callers_from_mutating_the_cached_frame():
    cache = TTLCache(ttl=60, copy=pd.DataFrame.copy)

    def loader():
        return pd.DataFrame({"player": ["A", "B"], "proj_fpts": [10.0, 5.0]})

    first = cache.get_or_load("key", loader)
    first.loc[0, "proj_fpts"] = 99.0
    first.drop(index=1, inplace=True)

    second = cache.get_or_load("key", loader)
    assert second["proj_fpts"].tolist() == [10.0, 5.0]


@pytest.fixture
def fresh_caches(monkeypatch):
    pool_cache = TTLCache(ttl=60, copy=pd.DataFrame.copy)
    monkeypatch.setattr(optimize_module, "_player_pool_cache", pool_cache)
    monkeypatch.setattr(helpers_module, "_latest_week_cache", TTLCache(ttl=60))


def test_optimizers_share_the_player_pool(fresh_caches, monkeypatch, pool):
    loads = []

    def fake_load(year, week):
        loads.append((year, week))
        return pool.copy()

    monkeypatch.setattr(optimize_module, "load_player_pool", fake_load)

    first = DFSLineupOptimizer(year=2025, week=3).get_projections_df()
    first.loc[0, "proj_fpts"] = 999.0
    second = DFSLineupOptimizer(year=2025, week=3).get_projections_df()
    DFSLineupOptimizer(year=2025, week=4).get_projections_df()

    assert loads == [(2025, 3), (2025, 4)]
    assert second.loc[0, "proj_fpts"] == pool.loc[0, "proj_fpts"]


def test_latest_week_is_cached_per_year(fresh_caches, monkeypatch):
    queries = []

    def fake_query(year):
        queries.append(year)
        return 4

    monkeypatch.setattr(helpers_module, "_query_latest_week", fake_query)

    for _ in range(3):
        assert helpers_module.get_latest_week(2026) == 4
    helpers_module.get_latest_week(2025)

    assert queries == [2026, 2025]
