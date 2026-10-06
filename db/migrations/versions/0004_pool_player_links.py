"""Link pool players to nflverse by name, team and week, not only by FantasyPros id.

Before 2024 most pool rows have no FantasyPros id, so player_week_results
found actual points for only about half of the players projected for 5+
points in those seasons. This adds:

- name_key(): the SQL twin of dfs_db.names.name_key (letters only, lower
  case, no Jr./Sr./II-V), so the two spellings of a name compare equal.
- pool_player_links: a materialized view giving pool rows a gsis_id other
  than through their own FantasyPros id, best first:
    "week"        a game log with the same name and team that week;
    "fantasypros" an id borrowed from the same name's other weeks (what
                  0003's view did on the fly);
    "name"        a week match carried to the same pool name's other weeks,
                  including weeks the player sat out, when that name only
                  ever matched one player.
  dfs_db.refresh_player_links() refreshes it after each game-log load and
  name cleanup. Precomputing the borrowed ids also keeps the view fast.
- player_week_results: a same-week match, else the row's own FantasyPros
  id, else the other links. On the 8,013 player-weeks with both a week match
  and a FantasyPros id, they agree on all but one, and that id was wrong.
- An index on player_game_logs (gsis_id), for one player's game log.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KNOWN_IDS = """
    known_ids AS (
        SELECT player, position, min(fp_player_id) AS fp_player_id
        FROM player_projections
        WHERE fp_player_id IS NOT NULL
        GROUP BY player, position
        HAVING count(DISTINCT fp_player_id) = 1
    )
"""

_RESULTS_COLUMNS = """
    pool.year,
    pool.week,
    pool.player,
    pool.position,
    pool.team,
    pool.opponent,
    pool.salary,
    pool.proj_fpts,
    pool.avg_fpts,
    linked.gsis_id,
    COALESCE(logs.dk_points, dst.dk_points) AS actual_dk_points,
    COALESCE(logs.game_id, dst.game_id) AS game_id
"""

_RESULTS_JOINS = """
    LEFT JOIN player_game_logs AS logs
      ON logs.year = pool.year
     AND logs.week = pool.week
     AND logs.gsis_id = linked.gsis_id
    LEFT JOIN dst_game_logs AS dst
      ON pool.position = 'DST'
     AND dst.year = pool.year
     AND dst.week = pool.week
     AND nfl_team(dst.team) = nfl_team(pool.team)
"""


def upgrade() -> None:
    op.execute(
        r"""
        CREATE FUNCTION name_key(name TEXT) RETURNS TEXT
        LANGUAGE sql IMMUTABLE PARALLEL SAFE
        RETURN regexp_replace(
            lower(regexp_replace(btrim(name), '\s+(jr\.?|sr\.?|ii|iii|iv|v)$', '', 'i')),
            '[^a-z]', '', 'g'
        )
        """
    )

    op.execute(
        "CREATE INDEX player_game_logs_gsis_id_idx ON player_game_logs (gsis_id)"
    )

    # Keys are computed once per side so the match is a hash join; comparing
    # name_key() pair by pair took 9 s against 0.2 s.
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW pool_player_links AS
        WITH pool AS (
            SELECT year, week, player, position, fp_player_id,
                   nfl_team(team) AS team, name_key(player) AS key
            FROM weekly_player_pool
            WHERE position <> 'DST'
        ),
        logs AS MATERIALIZED (
            SELECT year, week, gsis_id, nfl_team(team) AS team, name_key(player) AS key
            FROM player_game_logs
            WHERE (year, week) IN (SELECT year, week FROM pool)
        ),
        week_matches AS (
            SELECT pool.year, pool.week, pool.player, min(logs.gsis_id) AS gsis_id
            FROM pool
            JOIN logs USING (year, week, team, key)
            GROUP BY pool.year, pool.week, pool.player
            HAVING count(DISTINCT logs.gsis_id) = 1
        ),
        {_KNOWN_IDS},
        borrowed AS (
            SELECT pool.year, pool.week, pool.player, ids.gsis_id
            FROM pool
            JOIN known_ids AS known USING (player, position)
            JOIN nfl_players AS ids ON ids.fp_player_id = known.fp_player_id
            WHERE pool.fp_player_id IS NULL
        ),
        name_ids AS (
            SELECT pool.player, pool.position, min(matches.gsis_id) AS gsis_id
            FROM week_matches AS matches
            JOIN pool USING (year, week, player)
            GROUP BY pool.player, pool.position
            HAVING count(DISTINCT matches.gsis_id) = 1
        )
        SELECT pool.year, pool.week, pool.player,
               COALESCE(matches.gsis_id, borrowed.gsis_id, names.gsis_id) AS gsis_id,
               CASE WHEN matches.gsis_id IS NOT NULL THEN 'week'
                    WHEN borrowed.gsis_id IS NOT NULL THEN 'fantasypros'
                    ELSE 'name' END AS matched_by
        FROM pool
        LEFT JOIN week_matches AS matches USING (year, week, player)
        LEFT JOIN borrowed USING (year, week, player)
        LEFT JOIN name_ids AS names USING (player, position)
        WHERE COALESCE(matches.gsis_id, borrowed.gsis_id, names.gsis_id) IS NOT NULL
        """
    )
    # Unique, so it can be refreshed CONCURRENTLY without blocking readers.
    op.execute(
        "CREATE UNIQUE INDEX pool_player_links_key ON pool_player_links (year, week, player)"
    )
    op.execute(
        "COMMENT ON MATERIALIZED VIEW pool_player_links IS "
        "'Pool players matched to nflverse ids other than by their own FantasyPros "
        "id; refreshed after each game-log load.'"
    )

    op.execute(
        f"""
        CREATE OR REPLACE VIEW player_week_results AS
        SELECT {_RESULTS_COLUMNS}
        FROM weekly_player_pool AS pool
        LEFT JOIN nfl_players AS ids
          ON pool.position <> 'DST'
         AND ids.fp_player_id = pool.fp_player_id
        LEFT JOIN pool_player_links AS links
          ON links.year = pool.year
         AND links.week = pool.week
         AND links.player = pool.player
        CROSS JOIN LATERAL (
            SELECT COALESCE(
                CASE WHEN links.matched_by = 'week' THEN links.gsis_id END,
                ids.gsis_id,
                links.gsis_id
            ) AS gsis_id
        ) AS linked
        {_RESULTS_JOINS}
        """
    )


def downgrade() -> None:
    # 0003's view, verbatim apart from formatting.
    op.execute(
        f"""
        CREATE OR REPLACE VIEW player_week_results AS
        WITH {_KNOWN_IDS}
        SELECT {_RESULTS_COLUMNS}
        FROM weekly_player_pool AS pool
        LEFT JOIN known_ids AS known
          ON pool.fp_player_id IS NULL
         AND known.player = pool.player
         AND known.position = pool.position
        LEFT JOIN nfl_players AS ids
          ON pool.position <> 'DST'
         AND ids.fp_player_id = COALESCE(pool.fp_player_id, known.fp_player_id)
        CROSS JOIN LATERAL (SELECT ids.gsis_id) AS linked
        {_RESULTS_JOINS}
        """
    )
    op.execute("DROP MATERIALIZED VIEW IF EXISTS pool_player_links")
    op.execute("DROP INDEX IF EXISTS player_game_logs_gsis_id_idx")
    op.execute("DROP FUNCTION IF EXISTS name_key(TEXT)")
