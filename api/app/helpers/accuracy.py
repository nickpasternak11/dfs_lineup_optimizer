"""Turn the accuracy rows into the accuracy page's report: each projection
source's errors overall, by position, by week and by salary, plus how well
calibrated it was."""

import numpy as np
import pandas as pd
from dfs_common import accuracy

# What the page compares. A new source (DraftKings-scored projections, #42;
# our own model, #44) is a column in the rows query plus an entry here.
SOURCES = [
    {
        "key": "projection",
        "column": "proj_fpts",
        "label": "Projection",
        "description": "FantasyPros' full-PPR projection, which the optimizer uses",
    },
    {
        "key": "recent_avg",
        "column": "recent_avg",
        "label": "Recent avg",
        "description": "DraftKings points per game over the four weeks before "
        "(last season in week 1): the Avg column, as a baseline",
    },
]
SOURCE_KEYS = [source["key"] for source in SOURCES]
POSITIONS = ["QB", "RB", "WR", "TE", "DST"]
SALARY_TIERS = [(None, 4000), (4000, 6000), (6000, 8000), (8000, None)]


def _narrow(groups: dict[str, pd.DataFrame], **match) -> dict[str, pd.DataFrame]:
    """Keep the position-weeks matching every column=value given."""
    if not match:
        return groups
    narrowed = {}
    for key, frame in groups.items():
        keep = np.logical_and.reduce([frame[column] == value for column, value in match.items()])
        narrowed[key] = frame[keep]
    return narrowed


def _in_tier(df: pd.DataFrame, low: int | None, high: int | None) -> pd.DataFrame:
    keep = pd.Series(True, index=df.index)
    if low is not None:
        keep &= df.salary >= low
    if high is not None:
        keep &= df.salary < high
    return df[keep]


def build_report(
    rows: pd.DataFrame,
    year: int | None = None,
    position: str | None = None,
    min_proj: float = 5.0,
) -> dict:
    df = rows.rename(
        columns={**{s["column"]: s["key"] for s in SOURCES}, "actual_dk_points": "actual"}
    )
    complete = df.actual.notna() & df[SOURCE_KEYS].notna().all(axis=1)
    seasons = sorted(df.loc[complete, "year"].unique().tolist(), reverse=True)

    # A player counts when any source projected them for min_proj or more, so
    # the filter favors no source.
    relevant = df[df[SOURCE_KEYS].max(axis=1) >= min_proj]
    if year is not None:
        relevant = relevant[relevant.year == year]
    scoped = relevant if position is None else relevant[relevant.position == position]

    scored = scoped.actual.notna()
    evaluated_mask = complete.loc[scoped.index]
    coverage = {
        "considered": int(len(scoped)),
        "scored": int(scored.sum()),
        "no_stats": int((~scored & scoped.linked).sum()),
        "unlinked": int((~scoped.linked).sum()),
        "no_baseline": int((scored & ~evaluated_mask).sum()),
        "evaluated": int(evaluated_mask.sum()),
    }

    # By position ignores the position filter, so the table always compares
    # all five; everything else follows it.
    all_positions = relevant[complete.loc[relevant.index]]
    evaluated = scoped[evaluated_mask]
    groups = {key: accuracy.group_rank_correlations(all_positions, key) for key in SOURCE_KEYS}
    scoped_groups = _narrow(groups, **({} if position is None else {"position": position}))

    by_position = [
        {"position": pos, **accuracy.scorecard(subset, SOURCE_KEYS, _narrow(groups, position=pos))}
        for pos in POSITIONS
        if not (subset := all_positions[all_positions.position == pos]).empty
    ]
    by_week = [
        {
            "year": int(y),
            "week": int(w),
            **accuracy.scorecard(subset, SOURCE_KEYS, _narrow(scoped_groups, year=y, week=w)),
        }
        for (y, w), subset in evaluated.groupby(["year", "week"])
    ]
    # Ranking is judged within a position-week, which a salary tier cuts
    # across, so tiers get no rank correlation.
    by_salary = [
        {"low": low, "high": high, **accuracy.scorecard(subset, SOURCE_KEYS)}
        for low, high in SALARY_TIERS
        if not (subset := _in_tier(evaluated, low, high)).empty
    ]

    return {
        "seasons": seasons,
        "sources": [{k: s[k] for k in ("key", "label", "description")} for s in SOURCES],
        "year": year,
        "position": position,
        "min_proj": min_proj,
        "coverage": coverage,
        "summary": accuracy.scorecard(evaluated, SOURCE_KEYS, scoped_groups),
        "by_position": by_position,
        "by_week": by_week,
        "by_salary": by_salary,
        "calibration": {key: accuracy.calibration(evaluated, key) for key in SOURCE_KEYS},
    }
