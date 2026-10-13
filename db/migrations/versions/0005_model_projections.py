"""Our projection model's weekly projections, kept as snapshots.

dfs-projection-model's `predict` writes one row per pool player each time
it runs, stamped with when it ran, for players whose game hasn't kicked off.
Rows are never updated, so the accuracy page can score each player-week on
the last projection made before kickoff: a live record, with no hindsight.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE model_projections (
            year           SMALLINT      NOT NULL,
            week           SMALLINT      NOT NULL,
            player         TEXT          NOT NULL,
            generated_at   TIMESTAMPTZ   NOT NULL,
            position       TEXT          NOT NULL,
            team           TEXT,
            gsis_id        TEXT,
            proj_dk_points NUMERIC(6, 2) NOT NULL,
            model_version  TEXT          NOT NULL,

            CONSTRAINT model_projections_pkey PRIMARY KEY (year, week, player, generated_at)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE model_projections IS "
        "'Snapshots of our model''s DraftKings projections, written before kickoff "
        "by dfs-projection-model and never updated.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS model_projections")
