"""pool_player_links (migration 0004) is a materialized view matching pool
players to nflverse ids by name and team. It only changes when the game logs
or the pool's names do, so whatever writes those refreshes it."""

from sqlalchemy import text
from sqlalchemy.orm import Session

REFRESH_PLAYER_LINKS = text("REFRESH MATERIALIZED VIEW CONCURRENTLY pool_player_links")


def refresh_player_links(session: Session) -> None:
    # CONCURRENTLY keeps the view readable by the API while it rebuilds.
    session.execute(REFRESH_PLAYER_LINKS)
