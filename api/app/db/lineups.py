"""Saved lineups (lineup_snapshots) with the points their players scored,
and the best lineup possible in hindsight from the same players."""

from datetime import datetime

import pandas as pd
from dfs_db import get_engine
from sqlalchemy import text

from app.configs.configs import API_CACHE_TTL_SECONDS
from app.db.optimize import DFSLineupOptimizer, load_player_pool
from app.helpers.cache import TTLCache

WEEKS_QUERY = text("SELECT DISTINCT year, week FROM lineup_snapshots ORDER BY year DESC, week DESC")

# The week's latest snapshot of each phase (saved before the first game, and
# Sunday's late swap), each player with what they scored (NULL if they didn't
# play, or the game isn't final).
SNAPSHOT_QUERY = text(
    """
    WITH latest AS (
        SELECT phase, max(generated_at) AS generated_at
        FROM lineup_snapshots
        WHERE year = :year AND week = :week
        GROUP BY phase
    )
    SELECT saved.generated_at, saved.phase, saved.source, saved.strategy, saved.slot, saved.player,
           saved.position, saved.team, saved.salary, saved.projection,
           results.actual_dk_points AS actual
    FROM lineup_snapshots AS saved
    JOIN latest USING (phase, generated_at)
    LEFT JOIN player_week_results AS results
      ON results.year = saved.year
     AND results.week = saved.week
     AND results.player = saved.player
    WHERE saved.year = :year AND saved.week = :week
    ORDER BY saved.phase, saved.source, saved.strategy, saved.slot
    """
)

# Games the saved lineups could use (kicking off after they were saved) that
# aren't final yet.
UNFINISHED_GAMES_QUERY = text(
    """
    SELECT count(*) FROM nfl_games
    WHERE year = :year AND week = :week AND kickoff > :since AND home_score IS NULL
    """
)

_FLOATS = ["projection", "actual"]

# A week's hindsight-best lineup only changes with a stat correction, so it's
# kept an hour (unless caching is off).
_best_cache = TTLCache(3600 if API_CACHE_TTL_SECONDS > 0 else 0)


def snapshot_weeks() -> list[dict]:
    with get_engine().connect() as connection:
        return [{"year": int(y), "week": int(w)} for y, w in connection.execute(WEEKS_QUERY)]


def load_snapshot(year: int, week: int) -> pd.DataFrame:
    with get_engine().connect() as connection:
        df = pd.read_sql(SNAPSHOT_QUERY, connection, params={"year": year, "week": week})
    for column in _FLOATS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


def unfinished_games(year: int, week: int, since: datetime) -> int:
    with get_engine().connect() as connection:
        return int(connection.execute(UNFINISHED_GAMES_QUERY, {"year": year, "week": week, "since": since}).scalar())


def _solve_best(year: int, week: int, since: datetime) -> pd.DataFrame:
    pool = load_player_pool(year, week)
    kickoff = pd.to_datetime(pool["kickoff"], errors="coerce", utc=True)
    eligible = pool[kickoff.isna() | (kickoff > pd.Timestamp(since))].copy()
    if eligible["actual_dk_points"].isna().all():
        raise ValueError(f"No results yet for year={year}, week={week}")
    # A player who didn't play scored nothing.
    eligible["actual"] = eligible["actual_dk_points"].fillna(0.0)
    eligible["proj_fpts"] = eligible["actual"]
    optimizer = DFSLineupOptimizer.from_frame(eligible.reset_index(drop=True), year, week)
    return optimizer.optimize(include_started_players=True)


def best_lineup(year: int, week: int, since: datetime) -> pd.DataFrame:
    """The best lineup in hindsight: optimized on actual points over the
    players the saved lineups could pick from, with the default settings."""
    return _best_cache.get_or_load((year, week, since), lambda: _solve_best(year, week, since))
