"""Save the optimizer's suggested lineups before the games, for the weekly
review. The API owns the optimizer, so this asks it for the three lineups on
each projection source and stores them as a snapshot, never updated.

They're saved the morning of the week's first game, so they cover the whole
Thursday-to-Monday slate of a DraftKings classic contest. That's Thursday
most weeks, but a week can start on a Wednesday (Christmas), a Friday or a
Saturday.

A classic contest locks each player at their own game's kickoff, so on
Sunday, after inactives are out, each saved lineup gets a late swap: its
players whose games have started stay, and the rest are re-optimized on
fresh projections within the salary they left.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dfs_common.http import post
from dfs_db import LineupSnapshot, session_scope, upsert_dataframe

from src.configs import API_URL, log

SOURCES = ["fantasypros", "model"]
# The order the API returns them: the projection alone, then blended 90/10
# and 80/20 with the recent average.
STRATEGIES = ["projection", "blend_90_10", "blend_80_20"]
EASTERN = ZoneInfo("America/New_York")

# Each source's own projection in the pool's records.
SOURCE_COLUMNS = {"fantasypros": "proj_fpts", "model": "model_fpts"}


def before_first_kickoff(first_kickoff: datetime | None, now: datetime) -> bool:
    """Whether the week's lineups can still be saved: until its first game
    kicks off, the whole slate is open. Each save is a new snapshot, and the
    newest counts, so a later save replaces an earlier one. Once the first
    game starts, the lineups are locked; Sunday's late swap re-optimizes
    them."""
    return first_kickoff is None or now < first_kickoff


def is_first_game_day(first_kickoff: datetime | None, now: datetime) -> bool:
    """Whether `now` is the (Eastern) day of the week's first game, still
    before it kicks off."""
    if first_kickoff is None or now >= first_kickoff:
        return False
    return first_kickoff.astimezone(EASTERN).date() == now.astimezone(EASTERN).date()


def suggested_lineups(year: int, week: int) -> dict[str, list[list[dict]]]:
    """The API's default lineups on each source. A source it can't optimize
    (our model before it has projected the week) is skipped."""
    lineups = {}
    for source in SOURCES:
        try:
            response = post(f"{API_URL}/optimize", {"year": year, "week": week, "projection_source": source})
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (400, 404):
                log.warning("No %s lineups for %s week %s: %s", source, year, week, e.response.text)
                continue
            raise
        lineups[source] = response.json()
    return lineups


def pool_projections(year: int, week: int) -> pd.DataFrame:
    response = post(f"{API_URL}/projections", {"year": year, "week": week})
    return pd.DataFrame(response.json()).set_index("player")


def late_swap_requests(initial: pd.DataFrame, pool: pd.DataFrame, year: int, week: int, now: datetime) -> list[tuple]:
    """(source, strategy, optimize request) per saved lineup: its players
    whose games have started are locked in, every other started player is
    left out, and the optimizer fills the rest."""
    kickoff = pd.to_datetime(pool["kickoff"], utc=True, errors="coerce")
    started = set(pool.index[kickoff.notna() & (kickoff <= pd.Timestamp(now))])
    requests_ = []
    for (source, strategy), lineup in initial.groupby(["source", "strategy"], sort=False):
        locked = sorted(set(lineup.player) & started)
        requests_.append((source, strategy, {
            "year": year,
            "week": week,
            "projection_source": source,
            "include_started_players": True,
            "included_players": locked,
            "excluded_players": sorted(started - set(locked)),
        }))
    return requests_


def late_swap_lineups(requests_: list[tuple]) -> dict[str, list]:
    """Each source's swapped lineups, in STRATEGIES order (None where the
    API couldn't optimize one). The API returns all three strategies per
    request; only the one being swapped is kept."""
    lineups = {}
    for source, strategy, payload in requests_:
        try:
            response = post(f"{API_URL}/optimize", payload)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (400, 404):
                log.warning("No %s %s late swap: %s", source, strategy, e.response.text)
                continue
            raise
        lineups.setdefault(source, [None] * len(STRATEGIES))
        index = STRATEGIES.index(strategy)
        lineups[source][index] = response.json()[index]
    return lineups


def snapshot_rows(
    lineups: dict, pool: pd.DataFrame, year: int, week: int, now: datetime, phase: str = "initial"
) -> pd.DataFrame:
    rows = []
    for source, source_lineups in lineups.items():
        projections = pool[SOURCE_COLUMNS[source]]
        for strategy, lineup in zip(STRATEGIES, source_lineups):
            for slot, player in enumerate(lineup or []):
                rows.append({
                    "year": year,
                    "week": week,
                    "generated_at": now,
                    "source": source,
                    "strategy": strategy,
                    "phase": phase,
                    "slot": slot,
                    "player": player["player"],
                    "position": player["position"],
                    "team": player["team"],
                    "salary": player["salary"],
                    "projection": projections.get(player["player"]),
                    "optimized_points": player["proj_fpts"],
                })
    return pd.DataFrame(rows)


def store(rows: pd.DataFrame) -> int:
    with session_scope() as session:
        written = upsert_dataframe(session, LineupSnapshot, rows)
    log.info("Saved %s lineups (%s players)", written // 9, written)
    return written
