import math

import pandas as pd
import pytest
from dfs_common import accuracy


def frame(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["year", "week", "position", "proj", "base", "actual"])


def test_errors():
    df = frame([
        (2025, 1, "RB", 10.0, 0, 16.0),  # beat by 6
        (2025, 1, "RB", 10.0, 0, 7.0),  # missed by 3
    ])
    result = accuracy.errors(df.actual, df.proj)
    assert result["mae"] == 4.5
    assert result["bias"] == 1.5
    assert result["rmse"] == pytest.approx(math.sqrt((36 + 9) / 2))
    assert result["within"] == 0.5


def test_errors_of_nothing_are_none():
    assert accuracy.errors(pd.Series(dtype=float), pd.Series(dtype=float))["mae"] is None


def week(position, preds, actuals, base=None, year=2025, w=3):
    base = base or [0] * len(preds)
    return [(year, w, position, p, b, a) for p, b, a in zip(preds, base, actuals)]


def test_rank_correlation_is_judged_within_each_position_week():
    df = frame(
        # Ordered perfectly, though every RB scored 10 points under projection.
        week("RB", [20, 15, 10, 5, 1], [10, 5, 0, -1, -2])
        # Ordered exactly backwards.
        + week("WR", [20, 15, 10, 5, 1], [1, 5, 10, 15, 20])
    )
    groups = accuracy.group_rank_correlations(df, "proj")
    assert dict(zip(groups.position, groups.r)) == {"RB": pytest.approx(1.0), "WR": pytest.approx(-1.0)}
    assert accuracy.weighted_rank_correlation(groups) == pytest.approx(0.0)


def test_small_or_constant_groups_are_left_out():
    df = frame(
        week("QB", [20, 10, 5], [3, 2, 1])  # too few players
        + week("TE", [5, 5, 5, 5, 5], [1, 2, 3, 4, 5])  # projection can't rank them
        + week("RB", [5, 4, 3, 2, 1], [5, 4, 3, 2, 1])
    )
    groups = accuracy.group_rank_correlations(df, "proj")
    assert list(groups.position) == ["RB"]
    assert accuracy.weighted_rank_correlation(groups.iloc[0:0]) is None


def test_weighted_by_group_size():
    df = frame(
        week("RB", [5, 4, 3, 2, 1], [5, 4, 3, 2, 1], w=3)  # r = 1, five players
        + week("RB", list(range(15, 0, -1)), list(range(1, 16)), w=4)  # r = -1, fifteen
    )
    groups = accuracy.group_rank_correlations(df, "proj")
    assert accuracy.weighted_rank_correlation(groups) == pytest.approx((5 - 15) / 20)


def test_scorecard_compares_sources_on_the_same_rows():
    df = frame(week("RB", [20, 15, 10, 5, 1], [18, 15, 12, 2, 0], base=[10, 10, 10, 10, 10]))
    groups = {s: accuracy.group_rank_correlations(df, s) for s in ("proj", "base")}

    card = accuracy.scorecard(df, ["proj", "base"], groups)

    assert card["player_weeks"] == 5
    assert card["metrics"]["proj"]["mae"] == pytest.approx((2 + 0 + 2 + 3 + 1) / 5)
    assert card["metrics"]["proj"]["rank_corr"] == pytest.approx(1.0)
    # A flat baseline can't order anyone.
    assert card["metrics"]["base"]["rank_corr"] is None
    assert accuracy.scorecard(df, ["proj"])["metrics"]["proj"]["rank_corr"] is None


def test_calibration_bins_by_the_sources_own_value():
    df = frame([
        (2025, 1, "WR", 3.0, 0, 4.0),
        (2025, 1, "WR", -1.0, 0, 0.0),  # a DST can project below zero
        (2025, 1, "WR", 12.0, 0, 8.0),
        (2025, 1, "WR", 14.0, 0, 10.0),
        (2025, 1, "WR", 31.0, 0, 40.0),
    ])
    bins = accuracy.calibration(df, "proj")
    assert [(b["low"], b["high"], b["player_weeks"]) for b in bins] == [
        (None, 5.0, 2),
        (10.0, 15.0, 2),
        (25.0, None, 1),
    ]
    assert bins[1]["predicted"] == 13.0 and bins[1]["actual"] == 9.0
