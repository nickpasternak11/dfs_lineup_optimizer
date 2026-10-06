"""The accuracy page's rows (dfs_db.accuracy_rows), cached per worker."""

import pandas as pd
from dfs_db import get_engine
from dfs_db.accuracy_rows import ACCURACY_ROWS_QUERY, read_accuracy_rows

from app.configs.configs import API_CACHE_TTL_SECONDS
from app.helpers.cache import TTLCache

__all__ = ["ACCURACY_ROWS_QUERY", "load_rows"]

# One frame for every filter combination; it only changes with a scrape or a
# game-log load.
_rows_cache = TTLCache(API_CACHE_TTL_SECONDS, copy=pd.DataFrame.copy)


def _read_rows() -> pd.DataFrame:
    with get_engine().connect() as connection:
        return read_accuracy_rows(connection)


def load_rows() -> pd.DataFrame:
    return _rows_cache.get_or_load("rows", _read_rows)
