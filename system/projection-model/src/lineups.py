"""Save the optimizer's suggested lineups before the games, for the weekly
review. The API owns the optimizer, so this asks it for one lineup on each
projection source (FantasyPros, our model, and the two averaged) and stores
them as a snapshot, never updated. Every lineup uses SAVED_LINEUP_SETTINGS:
the QB stacked with one of his own pass catchers, no DST facing the lineup's
own players, and no second TE in FLEX.

They're saved shortly before the week's first kickoff, so they cover the
whole Thursday-to-Monday slate of a DraftKings classic contest. That's
Thursday night most weeks, but a week can start on a Wednesday (Christmas),
a Friday or a Saturday.

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
from dfs_common.lineups import SAVED_LINEUP_SETTINGS
from dfs_db import LineupSnapshot, session_scope, upsert_dataframe

from src.configs import API_URL, log

SOURCES = ["fantasypros", "model", "average"]
# The API returns three lineups per source: the projection alone, then
# blended 90/10 and 80/20 with the recent average. Only the projection's is
# saved: in the 2018-2026 backtest every blend built worse lineups than its
# plain projection. Weeks saved earlier have blend lineups, which a late
# swap still re-optimizes with their own strategy.
STRATEGY = "projection"
API_INDEX = {"projection": 0, "blend_90_10": 1, "blend_80_20": 2}
EASTERN = ZoneInfo("America/New_York")


def source_projection(pool: pd.DataFrame, source: str) -> pd.Series:
    """Each player's projection on `source`, from the pool's records."""
    if source == "average":
        return (pool["proj_fpts"] + pool["model_fpts"]) / 2
    return pool["model_fpts" if source == "model" else "proj_fpts"]


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


def suggested_lineups(year: int, week: int) -> dict[str, dict[str, list[dict]]]:
    """{source: {strategy: lineup}}: the API's projection lineup on each
    source, with SAVED_LINEUP_SETTINGS. A source it can't optimize (our
    model, or the average, before the model has projected the week) is
    skipped."""
    lineups = {}
    for source in SOURCES:
        try:
            response = post(
                f"{API_URL}/optimize",
                {"year": year, "week": week, "projection_source": source, **SAVED_LINEUP_SETTINGS},
            )
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (400, 404):
                log.warning("No %s lineups for %s week %s: %s", source, year, week, e.response.text)
                continue
            raise
        lineups[source] = {STRATEGY: response.json()[API_INDEX[STRATEGY]]}
    return lineups


def pool_projections(year: int, week: int) -> pd.DataFrame:
    response = post(f"{API_URL}/projections", {"year": year, "week": week})
    return pd.DataFrame(response.json()).set_index("player")


def games_left(pool: pd.DataFrame, now: datetime) -> bool:
    """Whether any pool player's game is still to start, so there's anything
    to swap."""
    kickoff = pd.to_datetime(pool["kickoff"], utc=True, errors="coerce")
    return bool((kickoff > pd.Timestamp(now)).any())


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
            **SAVED_LINEUP_SETTINGS,
        }))
    return requests_


def late_swap_lineups(requests_: list[tuple]) -> dict[str, dict[str, list[dict]]]:
    """{source: {strategy: lineup}} for each swapped lineup the API could
    optimize. The API returns all three strategies per request; only the one
    being swapped is kept."""
    lineups = {}
    for source, strategy, payload in requests_:
        try:
            response = post(f"{API_URL}/optimize", payload)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (400, 404):
                log.warning("No %s %s late swap: %s", source, strategy, e.response.text)
                continue
            raise
        lineups.setdefault(source, {})[strategy] = response.json()[API_INDEX[strategy]]
    return lineups


def snapshot_rows(
    lineups: dict, pool: pd.DataFrame, year: int, week: int, now: datetime, phase: str = "initial"
) -> pd.DataFrame:
    rows = []
    for source, source_lineups in lineups.items():
        projections = source_projection(pool, source)
        for strategy, lineup in source_lineups.items():
            for slot, player in enumerate(lineup):
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
