"""Add FantasyPros' player id to player_projections and weekly_player_pool.

The frontend builds player headshot URLs from it. Weeks scraped before this
revision keep it NULL until they are scraped again.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shared by upgrade and downgrade; only the trailing column differs.
POOL_VIEW = """
    CREATE OR REPLACE VIEW weekly_player_pool AS
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
        p.injury_type{extra}
    FROM player_projections AS p
    JOIN player_salaries AS s
      ON s.year = p.year
     AND s.week = p.week
     AND s.player = p.player
"""


def upgrade() -> None:
    op.execute("ALTER TABLE player_projections ADD COLUMN fp_player_id INTEGER")
    # CREATE OR REPLACE VIEW may only append columns, so it goes last.
    op.execute(POOL_VIEW.format(extra=",\n        p.fp_player_id"))


def downgrade() -> None:
    # A view can't drop a column in place.
    op.execute("DROP VIEW weekly_player_pool")
    op.execute(POOL_VIEW.format(extra=""))
    op.execute("ALTER TABLE player_projections DROP COLUMN fp_player_id")
