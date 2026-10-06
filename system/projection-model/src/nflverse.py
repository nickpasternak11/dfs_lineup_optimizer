"""Data the model reads directly from nflverse: snap counts (with the id map
that joins them to the game logs) and the schedule's game context."""

from io import BytesIO

import pandas as pd
from dfs_common.http import fetch

from src.configs import (
    FIRST_SNAP_SEASON,
    PLAYERS_URL,
    SCHEDULE_URL,
    SNAP_COUNTS_URL,
    log,
)


def read_csv(url: str) -> pd.DataFrame:
    response = fetch(url, timeout=120)
    return pd.read_csv(BytesIO(response.content), compression="gzip", low_memory=False)


def snap_counts(last_season: int) -> pd.DataFrame:
    """Offensive snaps per player per regular-season game, keyed by gsis_id."""
    ids = read_csv(PLAYERS_URL)[["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id")
    seasons = []
    for year in range(FIRST_SNAP_SEASON, last_season + 1):
        log.info("Downloading %s snap counts..", year)
        seasons.append(read_csv(SNAP_COUNTS_URL.format(year=year)))
    snaps = pd.concat(seasons, ignore_index=True)
    snaps = snaps[snaps.game_type == "REG"].merge(ids, left_on="pfr_player_id", right_on="pfr_id")
    return snaps.rename(columns={"season": "year", "offense_pct": "snap_share"})[
        ["year", "week", "gsis_id", "team", "offense_snaps", "snap_share"]
    ]


def schedule() -> pd.DataFrame:
    """Every game's rest days, roof and weather."""
    games = read_csv(SCHEDULE_URL)
    return games[["game_id", "home_team", "away_team", "home_rest", "away_rest", "roof", "wind", "temp"]]
