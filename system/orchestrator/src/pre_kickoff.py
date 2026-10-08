"""When to save the week's suggested lineups: shortly before its first kickoff.

A classic contest locks each player at their own game's kickoff, so the
whole slate stays open until the week's first game starts (usually Thursday
night, but not always: Thanksgiving, a Friday opener). Saving just before
it, after that game's inactives (out about 90 minutes before kickoff), gives
the lineups the news a player entering then would have.
"""

from datetime import datetime, timedelta

from dfs_db import get_engine
from sqlalchemy import text

# How long before the first kickoff the scrape, model run and save start:
# after its inactives, with time left for the jobs (a few minutes) to finish.
LEAD = timedelta(minutes=75)

# The week whose first kickoff is coming up within the lead and that has no
# lineups saved yet.
DUE_WEEK_QUERY = text(
    """
    SELECT g.year, g.week
    FROM nfl_games g
    GROUP BY g.year, g.week
    HAVING min(g.kickoff) > :now
       AND min(g.kickoff) <= :until
       AND NOT EXISTS (
           SELECT 1 FROM lineup_snapshots s
           WHERE s.year = g.year AND s.week = g.week AND s.phase = 'initial'
       )
    """
)


def due_week(now: datetime) -> tuple[int, int] | None:
    """(year, week) if that week's lineups should be saved now, else None.
    `now` must be timezone-aware."""
    with get_engine().connect() as connection:
        row = connection.execute(DUE_WEEK_QUERY, {"now": now, "until": now + LEAD}).first()
    return None if row is None else (row.year, row.week)
