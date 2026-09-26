"""Initial schema: player_salaries, player_projections, weekly_player_pool.

This is a straight port of the SQL that used to run once via Postgres's
docker-entrypoint-initdb.d on an empty volume. It is now the baseline for
every future migration instead.

If you already ran this project before Alembic was introduced, your database
has these objects but Alembic doesn't know that -- run `make db-stamp` once
(alembic stamp head) instead of `make db-upgrade` so it records this revision
as applied without re-running the DDL. A fresh volume should use
`make db-upgrade` as usual.

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE player_salaries (
            year          SMALLINT    NOT NULL,
            week          SMALLINT    NOT NULL,
            player        TEXT        NOT NULL,
            position      TEXT        NOT NULL,
            team          TEXT,
            opponent      TEXT,
            home          BOOLEAN,
            kickoff       TIMESTAMPTZ,
            salary        INTEGER,
            prev_salary   INTEGER,
            salary_change INTEGER,
            scraped_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT player_salaries_pkey PRIMARY KEY (year, week, player),
            CONSTRAINT player_salaries_year_check CHECK (year BETWEEN 2018 AND 2100),
            CONSTRAINT player_salaries_week_check CHECK (week BETWEEN 1 AND 22),
            CONSTRAINT player_salaries_salary_check CHECK (salary IS NULL OR salary >= 0)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE player_salaries IS "
        "'DraftKings salary + game context, written by dfs-salary-scraper.'"
    )

    op.execute(
        """
        CREATE TABLE player_projections (
            year          SMALLINT    NOT NULL,
            week          SMALLINT    NOT NULL,
            player        TEXT        NOT NULL,
            position      TEXT        NOT NULL,
            grade         TEXT,
            rank          INTEGER,
            min_rank      INTEGER,
            max_rank      INTEGER,
            avg_rank      NUMERIC(6, 2),
            std_rank      NUMERIC(6, 2),
            proj_fpts     NUMERIC(6, 2),
            avg_fpts      NUMERIC(6, 2),
            injury_status TEXT,
            injury_type   TEXT,
            scraped_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT player_projections_pkey PRIMARY KEY (year, week, player),
            CONSTRAINT player_projections_year_check CHECK (year BETWEEN 2018 AND 2100),
            CONSTRAINT player_projections_week_check CHECK (week BETWEEN 1 AND 22),
            CONSTRAINT player_projections_position_check
                CHECK (position IN ('QB', 'RB', 'WR', 'TE', 'DST'))
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE player_projections IS "
        "'FantasyPros rankings, grades and injuries, written by dfs-projection-scraper.'"
    )

    op.execute(
        """
        CREATE VIEW weekly_player_pool AS
        SELECT
            s.year,
            s.week,
            s.player,
            s.position,
            s.team,
            s.kickoff,
            s.opponent,
            s.home,
            p.grade,
            p.rank,
            p.avg_fpts,
            p.proj_fpts,
            s.salary,
            s.salary_change,
            ROUND(p.proj_fpts / (NULLIF(s.salary, 0) / 1000.0), 2) AS value,
            p.injury_status,
            p.injury_type
        FROM player_projections AS p
        JOIN player_salaries AS s
          ON s.year = p.year
         AND s.week = p.week
         AND s.player = p.player
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS weekly_player_pool")
    op.execute("DROP TABLE IF EXISTS player_projections")
    op.execute("DROP TABLE IF EXISTS player_salaries")
