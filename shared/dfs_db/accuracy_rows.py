"""Every past pool player-week with a final game: FantasyPros' projection, a
recent-average baseline and the DraftKings points scored. The API's accuracy
page and the projection model's backtest score the same rows."""

import pandas as pd
from sqlalchemy import Connection, text

# The baseline is the Avg column's DraftKings average, rebuilt for every past
# week from the games before it, so no week sees its own result. Our model's
# projection is the last snapshot it stored before the game's kickoff (none
# before it went live). Rows whose
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
        SELECT year, week, kickoff, home_team AS team FROM nfl_games WHERE home_score IS NOT NULL
        UNION ALL
        SELECT year, week, kickoff, away_team FROM nfl_games WHERE away_score IS NOT NULL
    )
    SELECT results.year, results.week, results.player, results.gsis_id,
           nfl_team(results.team) AS nfl_team, results.position, results.salary,
           results.proj_fpts, recent.recent_avg, live.proj_dk_points AS model_projection,
           results.actual_dk_points,
           (results.gsis_id IS NOT NULL OR results.position = 'DST') AS linked,
           live.model_version
    FROM results
    JOIN final_games AS final
      ON final.year = results.year
     AND final.week = results.week
     AND final.team = nfl_team(results.team)
    LEFT JOIN recent
      ON recent.year = results.year
     AND recent.week = results.week
     AND recent.player = results.player
    LEFT JOIN LATERAL (
        SELECT snapshot.proj_dk_points, snapshot.model_version
        FROM model_projections AS snapshot
        WHERE snapshot.year = results.year
          AND snapshot.week = results.week
          AND snapshot.player = results.player
          AND snapshot.generated_at < final.kickoff
        ORDER BY snapshot.generated_at DESC
        LIMIT 1
    ) AS live ON true
    """
)

FLOAT_COLUMNS = ["proj_fpts", "recent_avg", "model_projection", "actual_dk_points"]


def read_accuracy_rows(connection: Connection) -> pd.DataFrame:
    df = pd.read_sql(ACCURACY_ROWS_QUERY, connection)
    for column in FLOAT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df
