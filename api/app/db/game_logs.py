"""Read nflverse game logs (written by dfs-game-log-loader) for one player or
one team defense, with our projection for the weeks the pool covers."""

import pandas as pd
from dfs_db import get_engine
from sqlalchemy import text

# Score and home/away come from the schedule; both sides use nflverse codes.
_GAME_CONTEXT = """
    (games.home_team = logs.team) AS home,
    CASE WHEN games.home_team = logs.team THEN games.home_score ELSE games.away_score END AS team_score,
    CASE WHEN games.home_team = logs.team THEN games.away_score ELSE games.home_score END AS opponent_score
"""

PLAYER_BIO_QUERY = text(
    """
    SELECT gsis_id, player, position, birthdate, height, weight, college,
           draft_year, draft_round, draft_pick
    FROM nfl_players
    WHERE gsis_id = :gsis_id
    """
)

# The player's pool weeks are found once up front: correlating
# player_week_results per game instead re-evaluated the view for each row
# (~290 ms for a veteran, against ~40 ms).
PLAYER_GAMES_QUERY = text(
    f"""
    WITH pool AS (
        SELECT DISTINCT ON (year, week) year, week, proj_fpts, salary
        FROM player_week_results
        WHERE gsis_id = :gsis_id
        ORDER BY year, week
    )
    SELECT logs.year, logs.week, logs.season_type, logs.team, logs.opponent,
           {_GAME_CONTEXT},
           logs.dk_points, pool.proj_fpts, pool.salary,
           logs.completions, logs.attempts, logs.passing_yards, logs.passing_tds,
           logs.interceptions, logs.carries, logs.rushing_yards, logs.rushing_tds,
           logs.targets, logs.receptions, logs.receiving_yards, logs.receiving_tds,
           logs.fumbles_lost
    FROM player_game_logs AS logs
    LEFT JOIN nfl_games AS games ON games.game_id = logs.game_id
    LEFT JOIN pool ON pool.year = logs.year AND pool.week = logs.week
    WHERE logs.gsis_id = :gsis_id
    ORDER BY logs.year, logs.week
    """
)

DST_GAMES_QUERY = text(
    f"""
    SELECT logs.year, logs.week, logs.season_type, logs.team, logs.opponent,
           {_GAME_CONTEXT},
           logs.dk_points, pool.proj_fpts, pool.salary,
           logs.sacks, logs.interceptions, logs.fumble_recoveries, logs.defensive_tds,
           logs.return_tds, logs.safeties, logs.blocked_kicks, logs.points_allowed
    FROM dst_game_logs AS logs
    LEFT JOIN nfl_games AS games ON games.game_id = logs.game_id
    LEFT JOIN LATERAL (
        SELECT p.proj_fpts, p.salary
        FROM weekly_player_pool AS p
        WHERE p.position = 'DST'
          AND p.year = logs.year
          AND p.week = logs.week
          AND nfl_team(p.team) = nfl_team(logs.team)
        LIMIT 1
    ) AS pool ON true
    WHERE nfl_team(logs.team) = nfl_team(:team)
    ORDER BY logs.year, logs.week
    """
)

# NUMERIC comes back as Decimal.
_FLOAT_COLUMNS = ["dk_points", "proj_fpts", "sacks"]


def _read(query, params: dict) -> pd.DataFrame:
    with get_engine().connect() as connection:
        df = pd.read_sql(query, connection, params=params)
    for column in _FLOAT_COLUMNS:
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


def load_player_game_log(gsis_id: str) -> tuple[dict | None, pd.DataFrame]:
    bio = _read(PLAYER_BIO_QUERY, {"gsis_id": gsis_id})
    games = _read(PLAYER_GAMES_QUERY, {"gsis_id": gsis_id})
    return (None if bio.empty else bio.iloc[0].to_dict()), games


def load_dst_game_log(team: str) -> pd.DataFrame:
    return _read(DST_GAMES_QUERY, {"team": team})
