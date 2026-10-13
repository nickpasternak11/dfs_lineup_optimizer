"""Mark each saved lineup as the one saved before the week's first game
("initial") or Sunday's late swap ("late_swap").

A classic contest locks each player at their own game's kickoff, so
players whose games haven't started can still be swapped. On Sunday morning,
after inactives are out, dfs-projection-model keeps each saved lineup's
players whose games have started and re-optimizes the rest on fresh
projections; those lineups are saved as "late_swap". The review compares
both against the best lineup in hindsight.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Everything saved so far was saved before the week's first game.
    op.execute("ALTER TABLE lineup_snapshots ADD COLUMN phase TEXT NOT NULL DEFAULT 'initial'")


def downgrade() -> None:
    op.execute("ALTER TABLE lineup_snapshots DROP COLUMN phase")
