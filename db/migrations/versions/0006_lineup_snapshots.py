"""The lineups the optimizer suggested, saved before the games.

dfs-projection-model's `lineups` step asks the API for the three suggested
lineups on each projection source (FantasyPros, our model) every Sunday
morning and saves them here, one row per player. Rows are never updated, so
the weekly review scores exactly what was suggested before kickoff against
what the players scored and the best lineup possible in hindsight.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE lineup_snapshots (
            year             SMALLINT      NOT NULL,
            week             SMALLINT      NOT NULL,
            generated_at     TIMESTAMPTZ   NOT NULL,
            source           TEXT          NOT NULL,
            strategy         TEXT          NOT NULL,
            slot             SMALLINT      NOT NULL,
            player           TEXT          NOT NULL,
            position         TEXT          NOT NULL,
            team             TEXT,
            salary           INTEGER       NOT NULL,
            projection       NUMERIC(6, 2) NOT NULL,
            optimized_points NUMERIC(6, 2) NOT NULL,

            CONSTRAINT lineup_snapshots_pkey PRIMARY KEY (year, week, generated_at, source, strategy, slot)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE lineup_snapshots IS "
        "'The optimizer''s suggested lineups, saved before kickoff by "
        "dfs-projection-model and never updated.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS lineup_snapshots")
