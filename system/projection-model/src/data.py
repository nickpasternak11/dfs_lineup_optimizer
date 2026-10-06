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

GAMES_QUERY = text(
    "SELECT game_id, year, week, home_team, away_team, spread_line, total_line FROM nfl_games"
)

# NUMERIC comes back as Decimal.
_FLOATS = ["dk_points", "sacks", "spread_line", "total_line", "points_allowed"]


def _floats(df: pd.DataFrame) -> pd.DataFrame:
    for column in _FLOATS:
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


def load() -> dict[str, pd.DataFrame]:
    with get_engine().connect() as connection:
        return {
            "player_logs": _floats(pd.read_sql(PLAYER_LOGS_QUERY, connection)),
            "dst_logs": _floats(pd.read_sql(DST_LOGS_QUERY, connection)),
            "games": _floats(pd.read_sql(GAMES_QUERY, connection)),
            "pool": read_accuracy_rows(connection),
        }
