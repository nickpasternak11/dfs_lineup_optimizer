"""Save the optimizer's suggested lineups before the games, for the weekly
review. The API owns the optimizer, so this asks it for the three lineups on
each projection source and stores them as a snapshot, never updated."""

from datetime import datetime

import pandas as pd
import requests
from dfs_common.http import post
from dfs_db import LineupSnapshot, session_scope, upsert_dataframe

from src.configs import API_URL, log

SOURCES = ["fantasypros", "model"]
# The order the API returns them: the projection alone, then blended 90/10
# and 80/20 with the recent average.
STRATEGIES = ["projection", "blend_90_10", "blend_80_20"]
# Each source's own projection in the pool's records.
SOURCE_COLUMNS = {"fantasypros": "proj_fpts", "model": "model_fpts"}


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


def snapshot_rows(lineups: dict, pool: pd.DataFrame, year: int, week: int, now: datetime) -> pd.DataFrame:
    rows = []
    for source, source_lineups in lineups.items():
        projections = pool[SOURCE_COLUMNS[source]]
        for strategy, lineup in zip(STRATEGIES, source_lineups):
            for slot, player in enumerate(lineup):
                rows.append({
                    "year": year,
                    "week": week,
                    "generated_at": now,
                    "source": source,
                    "strategy": strategy,
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
