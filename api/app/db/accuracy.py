"""Every past pool player-week with a final game: the projection, a recent-
average baseline and the DraftKings points scored, for the accuracy page."""

import pandas as pd
from dfs_db import get_engine
from sqlalchemy import text

from app.configs.configs import API_CACHE_TTL_SECONDS
from app.helpers.cache import TTLCache

# The baseline is the Avg column's DraftKings average, rebuilt for every past
# week from the games before it, so no week sees its own result. Rows whose
# game isn't final yet are left out; a NULL actual on the rest means the
# player had no stats (linked) or couldn't be matched (not linked).
ACCURACY_ROWS_QUERY = text(
    """
    WITH results AS (
        SELECT year, week, player, position, team, salary, proj_fpts, gsis_id, actual_dk_points
        FROM player_week_results
    ),
    recent_weeks AS (
        -- The Avg column's window: the four weeks before, or last regular season in week 1.
        SELECT results.year, results.week, results.player, logs.dk_points
        FROM results
        JOIN player_game_logs AS logs
          ON logs.gsis_id = results.gsis_id
         AND logs.season_type = 'REG'
         AND CASE WHEN results.week = 1 THEN logs.year = results.year - 1
                  ELSE logs.year = results.year AND logs.week BETWEEN results.week - 4 AND results.week - 1 END
        UNION ALL
        SELECT results.year, results.week, results.player, dst.dk_points
        FROM results
        JOIN dst_game_logs AS dst
          ON results.position = 'DST'
         AND nfl_team(dst.team) = nfl_team(results.team)
         AND dst.season_type = 'REG'
         AND CASE WHEN results.week = 1 THEN dst.year = results.year - 1
                  ELSE dst.year = results.year AND dst.week BETWEEN results.week - 4 AND results.week - 1 END
    ),
    recent AS (
        SELECT year, week, player, avg(dk_points) AS recent_avg
        FROM recent_weeks
        GROUP BY year, week, player
    ),
    final_games AS (
        SELECT year, week, home_team AS team FROM nfl_games WHERE home_score IS NOT NULL
        UNION ALL
        SELECT year, week, away_team FROM nfl_games WHERE away_score IS NOT NULL
    )
    SELECT results.year, results.week, results.position, results.salary,
           results.proj_fpts, recent.recent_avg, results.actual_dk_points,
           (results.gsis_id IS NOT NULL OR results.position = 'DST') AS linked
    FROM results
    JOIN final_games AS final
      ON final.year = results.year
     AND final.week = results.week
     AND final.team = nfl_team(results.team)
    LEFT JOIN recent
      ON recent.year = results.year
     AND recent.week = results.week
     AND recent.player = results.player
    """
)

_FLOAT_COLUMNS = ["proj_fpts", "recent_avg", "actual_dk_points"]

# One frame for every filter combination; it only changes with a scrape or a
# game-log load.
_rows_cache = TTLCache(API_CACHE_TTL_SECONDS, copy=pd.DataFrame.copy)


def _read_rows() -> pd.DataFrame:
    with get_engine().connect() as connection:
        df = pd.read_sql(ACCURACY_ROWS_QUERY, connection)
    for column in _FLOAT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


def load_rows() -> pd.DataFrame:
    return _rows_cache.get_or_load("rows", _read_rows)
