"""nflverse game data: games, player and DST game logs, and player ids and bios.

Written by dfs-game-log-loader. Adds:

- nfl_games: schedule, final scores and closing Vegas lines.
- player_game_logs / dst_game_logs: weekly stats with DraftKings points.
- nfl_players: nflverse (GSIS) to FantasyPros ids, which is how game logs
  reach player_projections.fp_player_id, plus each player's bio.
- nfl_team(): one code per franchise, since nflverse and the salary page
  disagree on a few (LA/LAR, JAX/JAC, and OAK in 2018-19 nflverse schedules).
- player_week_results: every pool player's projection next to what they
  actually scored -- the basis for variance estimates and backtesting.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-04
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE nfl_games (
            game_id        TEXT        NOT NULL,
            year           SMALLINT    NOT NULL,
            week           SMALLINT    NOT NULL,
            game_type      TEXT        NOT NULL,
            kickoff        TIMESTAMPTZ,
            away_team      TEXT        NOT NULL,
            home_team      TEXT        NOT NULL,
            away_score     SMALLINT,
            home_score     SMALLINT,
            spread_line    NUMERIC(4, 1),
            total_line     NUMERIC(4, 1),
            away_moneyline INTEGER,
            home_moneyline INTEGER,
            scraped_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT nfl_games_pkey PRIMARY KEY (game_id)
        )
        """
    )
    op.execute("CREATE INDEX nfl_games_year_week_idx ON nfl_games (year, week)")
    op.execute(
        "COMMENT ON TABLE nfl_games IS "
        "'nflverse schedule: kickoff, final score and closing lines.'"
    )

    op.execute(
        """
        CREATE TABLE player_game_logs (
            year                  SMALLINT      NOT NULL,
            week                  SMALLINT      NOT NULL,
            gsis_id               TEXT          NOT NULL,
            player                TEXT          NOT NULL,
            position              TEXT          NOT NULL,
            team                  TEXT          NOT NULL,
            opponent              TEXT,
            game_id               TEXT,
            season_type           TEXT          NOT NULL,
            completions           SMALLINT      NOT NULL,
            attempts              SMALLINT      NOT NULL,
            passing_yards         SMALLINT      NOT NULL,
            passing_tds           SMALLINT      NOT NULL,
            interceptions         SMALLINT      NOT NULL,
            carries               SMALLINT      NOT NULL,
            rushing_yards         SMALLINT      NOT NULL,
            rushing_tds           SMALLINT      NOT NULL,
            targets               SMALLINT      NOT NULL,
            receptions            SMALLINT      NOT NULL,
            receiving_yards       SMALLINT      NOT NULL,
            receiving_tds         SMALLINT      NOT NULL,
            fumbles_lost          SMALLINT      NOT NULL,
            two_point_conversions SMALLINT      NOT NULL,
            other_tds             SMALLINT      NOT NULL,
            dk_points             NUMERIC(6, 2) NOT NULL,
            ppr_points            NUMERIC(6, 2),
            scraped_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),

            CONSTRAINT player_game_logs_pkey PRIMARY KEY (year, week, gsis_id)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE player_game_logs IS "
        "'nflverse weekly QB/RB/WR/TE stats with DraftKings points.'"
    )

    op.execute(
        """
        CREATE TABLE dst_game_logs (
            year              SMALLINT      NOT NULL,
            week              SMALLINT      NOT NULL,
            team              TEXT          NOT NULL,
            opponent          TEXT,
            game_id           TEXT,
            season_type       TEXT          NOT NULL,
            sacks             NUMERIC(4, 1) NOT NULL,
            interceptions     SMALLINT      NOT NULL,
            fumble_recoveries SMALLINT      NOT NULL,
            defensive_tds     SMALLINT      NOT NULL,
            return_tds        SMALLINT      NOT NULL,
            safeties          SMALLINT      NOT NULL,
            blocked_kicks     SMALLINT      NOT NULL,
            points_allowed    SMALLINT,
            dk_points         NUMERIC(6, 2) NOT NULL,
            scraped_at        TIMESTAMPTZ   NOT NULL DEFAULT now(),

            CONSTRAINT dst_game_logs_pkey PRIMARY KEY (year, week, team)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE dst_game_logs IS "
        "'nflverse weekly team defense/special teams stats with DraftKings points.'"
    )

    op.execute(
        """
        CREATE TABLE nfl_players (
            gsis_id      TEXT        NOT NULL,
            fp_player_id INTEGER     NOT NULL,
            player       TEXT        NOT NULL,
            position     TEXT,
            birthdate    DATE,
            height       SMALLINT,
            weight       SMALLINT,
            college      TEXT,
            draft_year   SMALLINT,
            draft_round  SMALLINT,
            draft_pick   SMALLINT,
            scraped_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT nfl_players_pkey PRIMARY KEY (gsis_id),
            CONSTRAINT nfl_players_fp_player_id_key UNIQUE (fp_player_id)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE nfl_players IS "
        "'nflverse (GSIS) and FantasyPros ids with bios, from the DynastyProcess crosswalk.'"
    )

    op.execute(
        """
        CREATE FUNCTION nfl_team(code TEXT) RETURNS TEXT
        LANGUAGE sql IMMUTABLE PARALLEL SAFE
        RETURN CASE upper(code)
            WHEN 'JAC' THEN 'JAX'
            WHEN 'LAR' THEN 'LA'
            WHEN 'STL' THEN 'LA'
            WHEN 'OAK' THEN 'LV'
            WHEN 'SD'  THEN 'LAC'
            WHEN 'WSH' THEN 'WAS'
            ELSE upper(code)
        END
        """
    )

    # A pool row gets its game log through its FantasyPros id. Weeks scraped
    # before fp_player_id existed borrow it from the same player's other
    # weeks, unless that name has ever carried two different ids. A NULL
    # actual_dk_points with a gsis_id means the player had no stats that week
    # (inactive, or the game hasn't been played); without one, he couldn't be
    # matched.
    op.execute(
        """
        CREATE VIEW player_week_results AS
        WITH known_ids AS (
            SELECT player, position, min(fp_player_id) AS fp_player_id
            FROM player_projections
            WHERE fp_player_id IS NOT NULL
            GROUP BY player, position
            HAVING count(DISTINCT fp_player_id) = 1
        )
        SELECT
            pool.year,
            pool.week,
            pool.player,
            pool.position,
            pool.team,
            pool.opponent,
            pool.salary,
            pool.proj_fpts,
            pool.avg_fpts,
            ids.gsis_id,
            COALESCE(logs.dk_points, dst.dk_points) AS actual_dk_points,
            COALESCE(logs.game_id, dst.game_id) AS game_id
        FROM weekly_player_pool AS pool
        LEFT JOIN known_ids AS known
          ON pool.fp_player_id IS NULL
         AND known.player = pool.player
         AND known.position = pool.position
        LEFT JOIN nfl_players AS ids
          ON pool.position <> 'DST'
         AND ids.fp_player_id = COALESCE(pool.fp_player_id, known.fp_player_id)
        LEFT JOIN player_game_logs AS logs
          ON logs.year = pool.year
         AND logs.week = pool.week
         AND logs.gsis_id = ids.gsis_id
        LEFT JOIN dst_game_logs AS dst
          ON pool.position = 'DST'
         AND dst.year = pool.year
         AND dst.week = pool.week
         AND nfl_team(dst.team) = nfl_team(pool.team)
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS player_week_results")
    op.execute("DROP FUNCTION IF EXISTS nfl_team(TEXT)")
    op.execute("DROP TABLE IF EXISTS nfl_players")
    op.execute("DROP TABLE IF EXISTS dst_game_logs")
    op.execute("DROP TABLE IF EXISTS player_game_logs")
    op.execute("DROP TABLE IF EXISTS nfl_games")
