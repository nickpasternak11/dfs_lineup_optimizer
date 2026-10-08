"""Read-only loads from the game-log tables."""

import pandas as pd
from dfs_db import get_engine
from dfs_db.accuracy_rows import read_accuracy_rows
from sqlalchemy import text

PLAYER_LOGS_QUERY = text(
    """
    SELECT year, week, gsis_id, player, position, team, opponent, game_id, season_type,
           attempts, carries, targets, receptions, passing_yards, passing_tds,
           interceptions, rushing_yards, rushing_tds, receiving_yards, receiving_tds,
           fumbles_lost, dk_points
    FROM player_game_logs
    """
)

DST_LOGS_QUERY = text(
    """
    SELECT year, week, team, opponent, game_id, season_type, sacks, interceptions,
           fumble_recoveries, points_allowed, dk_points
    FROM dst_game_logs
    """
)

INJURIES_QUERY = text(
    "SELECT year, week, gsis_id, team, report_status, practice_status FROM injury_reports"
)

GAMES_QUERY = text(
    "SELECT game_id, year, week, kickoff, home_team, away_team, spread_line, total_line FROM nfl_games"
)

# This week's pool, in nflverse team codes, with each player's gsis_id where
# player_week_results links one.
POOL_WEEK_QUERY = text(
    """
    SELECT pool.player, pool.position, pool.team AS pool_team,
           nfl_team(pool.team) AS team, results.gsis_id
    FROM weekly_player_pool AS pool
    LEFT JOIN player_week_results AS results
      ON results.year = pool.year
     AND results.week = pool.week
     AND results.player = pool.player
    WHERE pool.year = :year
      AND pool.week = :week
      AND pool.salary IS NOT NULL
    """
)

FIRST_KICKOFF_QUERY = text("SELECT min(kickoff) FROM nfl_games WHERE year = :year AND week = :week")

SAVED_LINEUPS_QUERY = text(
    "SELECT EXISTS (SELECT 1 FROM lineup_snapshots WHERE year = :year AND week = :week AND phase = :phase)"
)

# The week's latest lineups saved before its first game.
INITIAL_LINEUPS_QUERY = text(
    """
    SELECT source, strategy, slot, player
    FROM lineup_snapshots
    WHERE year = :year AND week = :week AND phase = 'initial'
      AND generated_at = (
          SELECT max(generated_at) FROM lineup_snapshots
          WHERE year = :year AND week = :week AND phase = 'initial'
      )
    ORDER BY source, strategy, slot
    """
)

LATEST_POOL_WEEK_QUERY = text(
    "SELECT max(week) FROM weekly_player_pool WHERE year = :year AND salary IS NOT NULL"
)

# NUMERIC comes back as Decimal.
_FLOATS = ["dk_points", "sacks", "spread_line", "total_line", "points_allowed"]


def _floats(df: pd.DataFrame) -> pd.DataFrame:
    for column in _FLOATS:
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


def load(accuracy_rows: bool = True) -> dict[str, pd.DataFrame]:
    """The game-log tables, and (for backtests) the accuracy page's rows."""
    with get_engine().connect() as connection:
        tables = {
            "player_logs": _floats(pd.read_sql(PLAYER_LOGS_QUERY, connection)),
            "dst_logs": _floats(pd.read_sql(DST_LOGS_QUERY, connection)),
            "games": _floats(pd.read_sql(GAMES_QUERY, connection)),
            "injuries": pd.read_sql(INJURIES_QUERY, connection),
        }
        if accuracy_rows:
            tables["pool"] = read_accuracy_rows(connection)
    tables["games"]["kickoff"] = pd.to_datetime(tables["games"].kickoff, utc=True)
    return tables


def latest_pool_week(year: int) -> int | None:
    with get_engine().connect() as connection:
        return connection.execute(LATEST_POOL_WEEK_QUERY, {"year": year}).scalar()


def load_pool_week(year: int, week: int) -> pd.DataFrame:
    with get_engine().connect() as connection:
        return pd.read_sql(POOL_WEEK_QUERY, connection, params={"year": year, "week": week})


def first_kickoff(year: int, week: int):
    """The week's first kickoff (timezone-aware), or None."""
    with get_engine().connect() as connection:
        return connection.execute(FIRST_KICKOFF_QUERY, {"year": year, "week": week}).scalar()


def has_saved_lineups(year: int, week: int, phase: str = "initial") -> bool:
    with get_engine().connect() as connection:
        return bool(connection.execute(SAVED_LINEUPS_QUERY, {"year": year, "week": week, "phase": phase}).scalar())


def load_initial_lineups(year: int, week: int) -> pd.DataFrame:
    with get_engine().connect() as connection:
        return pd.read_sql(INITIAL_LINEUPS_QUERY, connection, params={"year": year, "week": week})
