"""Decide which of this week's scheduled scrapes are missing from the database.

The schedule only fires at fixed times, so a run missed while the stack was
down would otherwise never happen -- and past seasons' salaries can only be
collected during their week, so a missed Tuesday backfill loses them for a
year.
"""

from datetime import datetime

from dfs_db import get_engine
from sqlalchemy import text

# September through February: regular season and playoffs. Outside it
# FantasyPros has no current-week data, so every scrape would just fail.
SEASON_MONTHS = {9, 10, 11, 12, 1, 2}

COUNT_ROWS = {
    table: text(f"SELECT count(*) FROM {table} WHERE year = :year AND week = :week")
    for table in ("player_salaries", "player_projections")
}


def in_season(now: datetime) -> bool:
    return now.month in SEASON_MONTHS


def catch_up_allowed(now: datetime) -> bool:
    """False until the week's own Tuesday runs have had their chance.

    Monday and early Tuesday are also when the week number rolls over before
    the salary page does, so catching up then could file last week's salaries
    under the new week. `now` must be US Eastern time.
    """
    if not in_season(now):
        return False
    if now.weekday() == 0:  # Monday
        return False
    return not (now.weekday() == 1 and now.hour < 10)  # Tuesday before 10:00


def missing_jobs(season: int, week: int) -> list[str]:
    """Which of salaries, projections and backfill have no rows this week."""
    with get_engine().connect() as connection:

        def has_rows(table: str, year: int) -> bool:
            params = {"year": year, "week": week}
            return connection.execute(COUNT_ROWS[table], params).scalar() > 0

        missing = []
        if not has_rows("player_salaries", season):
            missing.append("salaries")
        if not has_rows("player_projections", season):
            missing.append("projections")
        # Last season stands in for the whole backfill range: the backfill
        # writes every season in one run.
        if not (
            has_rows("player_salaries", season - 1)
            and has_rows("player_projections", season - 1)
        ):
            missing.append("backfill")
        return missing
