"""How close projections came to actual DraftKings points.

Shared by the API's accuracy page and offline model work (#44). Every
function takes one row per player-week with an `actual` column and one column
per projection source, and compares the sources on the same rows.
"""

import math

import numpy as np
import pandas as pd

# A projection counts as close when it landed within this many points.
WITHIN = 5.0

# The optimizer chooses between players at one position in one week, so
# that's where a source's ordering of players is judged.
RANK_GROUPS = ["year", "week", "position"]
MIN_GROUP = 5

CALIBRATION_EDGES = [-math.inf, 5, 10, 15, 20, 25, math.inf]


def errors(actual: pd.Series, predicted: pd.Series) -> dict[str, float | None]:
    """Mean absolute error, bias (positive: players beat the projection),
    RMSE, and the share within WITHIN points."""
    if actual.empty:
        return {"mae": None, "bias": None, "rmse": None, "within": None}
    error = actual - predicted
    return {
        "mae": float(error.abs().mean()),
        "bias": float(error.mean()),
        "rmse": float(np.sqrt((error**2).mean())),
        "within": float((error.abs() <= WITHIN).mean()),
    }


def group_rank_correlations(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Spearman correlation between `source` and `actual` in each position-week
    (columns RANK_GROUPS + n, r). Groups smaller than MIN_GROUP, or where
    either side is constant, are left out.

    Computed from rank sums rather than per group, so a few hundred groups
    cost one groupby.
    """
    if df.empty:
        return pd.DataFrame(columns=[*RANK_GROUPS, "n", "r"])
    grouped = df.groupby(RANK_GROUPS)
    x = grouped[source].rank()
    y = grouped["actual"].rank()
    keys = [df[column] for column in RANK_GROUPS]
    sums = pd.DataFrame({"x": x, "y": y, "xx": x * x, "yy": y * y, "xy": x * y}).groupby(keys).sum()
    n = grouped.size()
    cov = sums.xy - sums.x * sums.y / n
    var_x = sums.xx - sums.x**2 / n
    var_y = sums.yy - sums.y**2 / n
    with np.errstate(divide="ignore", invalid="ignore"):
        r = cov / np.sqrt(var_x * var_y)
    out = pd.DataFrame({"n": n, "r": r}).reset_index()
    return out[(out.n >= MIN_GROUP) & np.isfinite(out.r)].reset_index(drop=True)


def weighted_rank_correlation(groups: pd.DataFrame) -> float | None:
    """The groups' correlations averaged, each weighted by its player count."""
    if groups.empty:
        return None
    return float((groups.r * groups.n).sum() / groups.n.sum())


def scorecard(
    df: pd.DataFrame,
    sources: list[str],
    rank_groups: dict[str, pd.DataFrame] | None = None,
) -> dict:
    """Each source's errors over df's rows, plus its rank correlation over the
    position-weeks in `rank_groups` (from group_rank_correlations, already
    narrowed to this slice), or None when ranking doesn't apply to the slice."""
    metrics = {}
    for source in sources:
        card = errors(df["actual"], df[source])
        groups = None if rank_groups is None else rank_groups[source]
        card["rank_corr"] = None if groups is None else weighted_rank_correlation(groups)
        metrics[source] = card
    return {"player_weeks": int(len(df)), "metrics": metrics}


def calibration(df: pd.DataFrame, source: str) -> list[dict]:
    """Average actual points for each range of the source's projection: a
    calibrated source's players score about what it projected in every range."""
    edges = CALIBRATION_EDGES
    bins = pd.cut(df[source], edges, right=False)
    grouped = df.groupby(bins, observed=True)
    stats = grouped.agg(n=("actual", "size"), predicted=(source, "mean"), actual=("actual", "mean"))
    out = []
    for interval, row in stats.iterrows():
        out.append(
            {
                "low": None if math.isinf(interval.left) else float(interval.left),
                "high": None if math.isinf(interval.right) else float(interval.right),
                "player_weeks": int(row.n),
                "predicted": float(row.predicted),
                "actual": float(row.actual),
            }
        )
    return out
