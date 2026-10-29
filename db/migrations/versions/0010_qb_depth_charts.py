"""Each team's latest QB depth chart, from nflverse.

dfs-game-log-loader writes one row per QB in order on his team's latest
depth chart for the current season. The charts keep an injured starter at
the top, so the projection model takes the highest-ranked QB who isn't
ruled out as the starter and projects the others at 0.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-29
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE qb_depth_charts (
            year       SMALLINT    NOT NULL,
            team       TEXT        NOT NULL,
            gsis_id    TEXT        NOT NULL,
            player     TEXT        NOT NULL,
            depth      SMALLINT    NOT NULL,
            charted_at TIMESTAMPTZ NOT NULL,
            scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT qb_depth_charts_pkey PRIMARY KEY (year, team, gsis_id)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE qb_depth_charts IS "
        "'Each team''s QBs in order on its latest depth chart, from nflverse.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS qb_depth_charts")
