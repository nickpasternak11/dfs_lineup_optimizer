"""ORM mappings for the scraped tables and the nflverse game data.

Base.metadata is what db/migrations/env.py autogenerates Alembic revisions
against, so a column added here and not migrated (or migrated and not added
here) will drift, and `make test-db` will fail. The weekly_player_pool and
player_week_results views are not mapped -- they have no primary key for the
ORM to track -- and live only in the Alembic revisions that created them.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
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
    __table_args__ = {
        "comment": "DraftKings salary + game context, written by dfs-salary-scraper."
    }

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
    __table_args__ = {
        "comment": "FantasyPros rankings, grades and injuries, written by dfs-projection-scraper."
    }

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
    # FantasyPros' id for the player; the frontend builds headshot URLs from it.
    fp_player_id: Mapped[int | None] = mapped_column(Integer)


def _scraped_at() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# nflverse tables, written by dfs-game-log-loader. Team codes are stored as
# nflverse publishes them (LA for the Rams, OAK for 2018-19 Raiders games);
# the SQL function nfl_team() maps them onto the salary scraper's codes.


class NflGame(Base):
    __tablename__ = "nfl_games"
    __table_args__ = (
        Index("nfl_games_year_week_idx", "year", "week"),
        {"comment": "nflverse schedule: kickoff, final score and closing lines."},
    )

    game_id: Mapped[str] = mapped_column(Text, primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    game_type: Mapped[str] = mapped_column(Text, nullable=False)
    kickoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    away_team: Mapped[str] = mapped_column(Text, nullable=False)
    home_team: Mapped[str] = mapped_column(Text, nullable=False)
    away_score: Mapped[int | None] = mapped_column(SmallInteger)
    home_score: Mapped[int | None] = mapped_column(SmallInteger)
    # Points the home team is favored by (negative: the away team is).
    spread_line: Mapped[float | None] = mapped_column(Numeric(4, 1))
    total_line: Mapped[float | None] = mapped_column(Numeric(4, 1))
    away_moneyline: Mapped[int | None] = mapped_column(Integer)
    home_moneyline: Mapped[int | None] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = _scraped_at()


class PlayerGameLog(Base):
    __tablename__ = "player_game_logs"
    __table_args__ = {
        "comment": "nflverse weekly QB/RB/WR/TE stats with DraftKings points."
    }

    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    week: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    gsis_id: Mapped[str] = mapped_column(Text, primary_key=True)
    player: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    team: Mapped[str] = mapped_column(Text, nullable=False)
    opponent: Mapped[str | None] = mapped_column(Text)
    game_id: Mapped[str | None] = mapped_column(Text)
    season_type: Mapped[str] = mapped_column(Text, nullable=False)
    completions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    passing_yards: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    passing_tds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    interceptions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    carries: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rushing_yards: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rushing_tds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    targets: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    receptions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    receiving_yards: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    receiving_tds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fumbles_lost: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    two_point_conversions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Kick/punt return and offensive fumble-recovery touchdowns.
    other_tds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    dk_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    # nflverse's own full-PPR total, kept for comparison.
    ppr_points: Mapped[float | None] = mapped_column(Numeric(6, 2))
    scraped_at: Mapped[datetime] = _scraped_at()


class DstGameLog(Base):
    __tablename__ = "dst_game_logs"
    __table_args__ = {
        "comment": "nflverse weekly team defense/special teams stats with DraftKings points."
    }

    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    week: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    team: Mapped[str] = mapped_column(Text, primary_key=True)
    opponent: Mapped[str | None] = mapped_column(Text)
    game_id: Mapped[str | None] = mapped_column(Text)
    season_type: Mapped[str] = mapped_column(Text, nullable=False)
    sacks: Mapped[float] = mapped_column(Numeric(4, 1), nullable=False)
    interceptions: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fumble_recoveries: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    defensive_tds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    return_tds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    safeties: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    blocked_kicks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    points_allowed: Mapped[int | None] = mapped_column(SmallInteger)
    dk_points: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    scraped_at: Mapped[datetime] = _scraped_at()


class PlayerIdMap(Base):
    __tablename__ = "player_id_map"
    __table_args__ = {
        "comment": "nflverse (GSIS) to FantasyPros player ids, from the DynastyProcess crosswalk."
    }

    gsis_id: Mapped[str] = mapped_column(Text, primary_key=True)
    fp_player_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    player: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[str | None] = mapped_column(Text)
    scraped_at: Mapped[datetime] = _scraped_at()


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
    "fp_player_id",
]
