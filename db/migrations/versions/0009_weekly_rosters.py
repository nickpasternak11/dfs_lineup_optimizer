"""Weekly roster statuses, from nflverse.

dfs-game-log-loader writes one row per QB, RB, WR and TE per week from
2016: their team and roster status (active, reserve lists, practice squad,
released...). Players on a reserve list aren't on the injury report, so this
is how the projection model knows they can't play.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE weekly_rosters (
            year          SMALLINT    NOT NULL,
            week          SMALLINT    NOT NULL,
            gsis_id       TEXT        NOT NULL,
            season_type   TEXT        NOT NULL,
            team          TEXT        NOT NULL,
            player        TEXT        NOT NULL,
            position      TEXT        NOT NULL,
            status        TEXT        NOT NULL,
            status_detail TEXT,
            scraped_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT weekly_rosters_pkey PRIMARY KEY (year, week, gsis_id)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE weekly_rosters IS "
        "'Each week''s roster status for QBs, RBs, WRs and TEs, from nflverse.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS weekly_rosters")
