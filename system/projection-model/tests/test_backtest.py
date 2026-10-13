import pandas as pd
import pytest
from src import backtest


def pool_row(year, week, player, gsis_id, team, position, proj, recent, actual):
    return {
        "year": year, "week": week, "player": player, "gsis_id": gsis_id, "nfl_team": team,
        "position": position, "salary": 5000, "proj_fpts": proj, "recent_avg": recent,
        "actual_dk_points": actual, "linked": True,
    }


def test_predictions_join_players_by_id_and_defenses_by_team():
    pool = pd.DataFrame([
        pool_row(2025, 3, "Josh Allen", "00-1", "BUF", "QB", 22.0, 24.0, 30.0),
        pool_row(2025, 3, "Bills", None, "BUF", "DST", 7.0, 6.0, 9.0),
        pool_row(2025, 3, "Nobody", "00-9", "NE", "WR", 8.0, 7.0, 3.0),
    ])
    predictions = pd.DataFrame([
        {"year": 2025, "week": 3, "gsis_id": "00-1", "team": "BUF", "position": "QB", "model": 25.0},
        {"year": 2025, "week": 3, "gsis_id": None, "team": "BUF", "position": "DST", "model": 8.0},
    ])
    joined = backtest.attach_predictions(pool, predictions).set_index("player")
    assert joined.loc["Josh Allen", "model"] == 25.0
    assert joined.loc["Bills", "model"] == 8.0
    assert pd.isna(joined.loc["Nobody", "model"])


def test_comparison_rows_need_every_source_and_an_actual():
    pool = pd.DataFrame([
        pool_row(2025, 3, "A", "1", "BUF", "WR", 10.0, 9.0, 12.0),
        pool_row(2025, 3, "B", "2", "BUF", "WR", 10.0, None, 12.0),  # no recent games
        pool_row(2025, 3, "C", "3", "BUF", "WR", 10.0, 9.0, None),  # inactive
        pool_row(2025, 3, "D", "4", "BUF", "WR", 2.0, 2.0, 12.0),  # nobody projected 5+
    ]).assign(model=[11.0, 11.0, 11.0, 6.0])
    rows = backtest.comparison_rows(pool)
    assert list(rows.player) == ["A", "D"]  # D counts: the model projected 6
    assert rows.set_index("player").loc["A", "blend"] == pytest.approx(10.5)


def test_report_lists_every_source():
    rows = backtest.comparison_rows(pd.DataFrame([
        pool_row(2025, 3, str(i), str(i), "BUF", "WR", 10.0 + i, 9.0, 8.0 + 2 * i) for i in range(6)
    ]).assign(model=[10.0, 11.0, 12.0, 13.0, 14.0, 15.0]))
    report = backtest.format_report(rows)
    assert "6 player-weeks, 2025-2025" in report
    for label in ("FantasyPros", "Recent avg", "Model", "Model+FP blend"):
        assert label in report
