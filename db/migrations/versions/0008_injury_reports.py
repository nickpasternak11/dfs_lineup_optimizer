"""The NFL's weekly injury reports, from nflverse.

dfs-game-log-loader writes one row per listed player per week: the final
game status (Out, Doubtful, Questionable; Probable until 2015) and the
week's latest practice participation. Final statuses come out the day
before a Thursday game and on Friday for Sunday games, ahead of the
projection model's runs, so the model can tell who won't play.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE injury_reports (
            year            SMALLINT    NOT NULL,
            week            SMALLINT    NOT NULL,
            gsis_id         TEXT        NOT NULL,
            season_type     TEXT        NOT NULL,
            team            TEXT        NOT NULL,
            player          TEXT        NOT NULL,
            position        TEXT,
            report_status   TEXT,
            report_injury   TEXT,
            practice_status TEXT,
            practice_injury TEXT,
            scraped_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT injury_reports_pkey PRIMARY KEY (year, week, gsis_id)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE injury_reports IS "
        "'The NFL''s weekly injury reports from nflverse: final game status "
        "and practice participation.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS injury_reports")
