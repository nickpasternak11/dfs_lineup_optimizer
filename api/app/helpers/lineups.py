"""The weekly review: how each saved lineup scored, before and after Sunday's
late swap, against the best lineup possible in hindsight."""

import pandas as pd

from app.db import lineups as lineups_db

SOURCE_ORDER = ["fantasypros", "model"]
STRATEGY_ORDER = ["projection", "blend_90_10", "blend_80_20"]
PHASE_ORDER = ["initial", "late_swap"]


def _players(df: pd.DataFrame) -> list[dict]:
    records = df[["slot", "player", "position", "team", "salary", "projection", "actual"]]
    return [
        {key: (None if pd.isna(value) else value) for key, value in record.items()}
        for record in records.to_dict(orient="records")
    ]


def _lineups(snapshot: pd.DataFrame) -> list[dict]:
    out = []
    for (phase, source, strategy), players in snapshot.groupby(["phase", "source", "strategy"]):
        out.append({
            "phase": phase,
            "source": source,
            "strategy": strategy,
            "projected": round(float(players.projection.sum()), 2),
            "actual": round(float(players.actual.fillna(0).sum()), 2),
            "players": _players(players.sort_values("slot")),
        })
    order = {
        key: i for i, key in enumerate((s, t, p) for s in SOURCE_ORDER for t in STRATEGY_ORDER for p in PHASE_ORDER)
    }
    return sorted(
        out, key=lambda lineup: order.get((lineup["source"], lineup["strategy"], lineup["phase"]), len(order))
    )


def _best(year: int, week: int, since) -> dict | None:
    try:
        best = lineups_db.best_lineup(year, week, since)
    except (ValueError, FileNotFoundError):
        return None
    players = best.assign(slot=None, projection=None)[["slot", "player", "position", "team", "salary", "projection", "actual"]]
    return {"actual": round(float(best.actual.sum()), 2), "players": _players(players)}


def build_review(year: int | None = None, week: int | None = None) -> dict:
    weeks = lineups_db.snapshot_weeks()
    empty = {"weeks": weeks, "year": year, "week": week, "saved_at": None, "swapped_at": None,
             "complete": False, "lineups": [], "best": None, "season": []}
    if not weeks:
        return empty

    snapshots = {}

    def snapshot(y: int, w: int) -> pd.DataFrame:
        if (y, w) not in snapshots:
            snapshots[(y, w)] = lineups_db.load_snapshot(y, w)
        return snapshots[(y, w)]

    def saved_at(df: pd.DataFrame, phase: str = "initial"):
        """When a phase's lineups were saved. The first save sets the slate
        (the late swap can only use its players); a late swap may be missing."""
        times = df.loc[df.phase == phase, "generated_at"]
        if times.empty:
            return df.generated_at.min().to_pydatetime() if phase == "initial" else None
        return times.iloc[0].to_pydatetime()

    def complete(y: int, w: int) -> bool:
        return lineups_db.unfinished_games(y, w, saved_at(snapshot(y, w))) == 0

    if year is None or week is None:
        # The newest week whose games are all final, else the newest saved.
        finished = next((ref for ref in weeks if complete(ref["year"], ref["week"])), weeks[0])
        year, week = finished["year"], finished["week"]
    if snapshot(year, week).empty:
        return {**empty, "year": year, "week": week}

    season = []
    for ref in sorted((w for w in weeks if w["year"] == year), key=lambda w: w["week"]):
        week_snapshot = snapshot(year, ref["week"])
        week_best = _best(year, ref["week"], saved_at(week_snapshot))
        season.append({
            "week": ref["week"],
            "complete": complete(year, ref["week"]),
            "best": None if week_best is None else week_best["actual"],
            "lineups": [
                {k: lineup[k] for k in ("phase", "source", "strategy", "projected", "actual")}
                for lineup in _lineups(week_snapshot)
            ],
        })

    return {
        "weeks": weeks,
        "year": year,
        "week": week,
        "saved_at": saved_at(snapshot(year, week)),
        "swapped_at": saved_at(snapshot(year, week), "late_swap"),
        "complete": complete(year, week),
        "lineups": _lineups(snapshot(year, week)),
        "best": _best(year, week, saved_at(snapshot(year, week))),
        "season": season,
    }
