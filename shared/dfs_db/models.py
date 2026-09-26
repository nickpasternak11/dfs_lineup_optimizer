"""ORM mappings for player_salaries and player_projections.

Base.metadata is what db/migrations/env.py autogenerates Alembic revisions
against, so a column added here and not migrated (or migrated and not added
here) will drift. The weekly_player_pool view is not mapped -- it has no
primary key for the ORM to track -- and lives only in the Alembic revision
that created it.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlayerSalary(Base):
    __tablename__ = "player_salaries"

    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    week: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    player: Mapped[str] = mapped_column(Text, primary_key=True)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    team: Mapped[str | None] = mapped_column(Text)
    opponent: Mapped[str | None] = mapped_column(Text)
    home: Mapped[bool | None] = mapped_column(Boolean)
    kickoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    salary: Mapped[int | None] = mapped_column(Integer)
    prev_salary: Mapped[int | None] = mapped_column(Integer)
    salary_change: Mapped[int | None] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PlayerProjection(Base):
    __tablename__ = "player_projections"

    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    week: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    player: Mapped[str] = mapped_column(Text, primary_key=True)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    grade: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[int | None] = mapped_column(Integer)
    min_rank: Mapped[int | None] = mapped_column(Integer)
    max_rank: Mapped[int | None] = mapped_column(Integer)
    avg_rank: Mapped[float | None] = mapped_column(Numeric(6, 2))
    std_rank: Mapped[float | None] = mapped_column(Numeric(6, 2))
    proj_fpts: Mapped[float | None] = mapped_column(Numeric(6, 2))
    avg_fpts: Mapped[float | None] = mapped_column(Numeric(6, 2))
    injury_status: Mapped[str | None] = mapped_column(Text)
    injury_type: Mapped[str | None] = mapped_column(Text)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


WEEKLY_PLAYER_POOL_COLUMNS = [
    "year",
    "week",
    "player",
    "position",
    "team",
    "kickoff",
    "opponent",
    "home",
    "grade",
    "rank",
    "avg_fpts",
    "proj_fpts",
    "salary",
    "salary_change",
    "value",
    "injury_status",
    "injury_type",
]
