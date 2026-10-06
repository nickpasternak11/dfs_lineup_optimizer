import re

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.application import application
from app.db import accuracy as accuracy_db
from app.helpers.accuracy import build_report
from app.models.responses.accuracy import AccuracyResponse

client = TestClient(application)


def rows(*players, year=2025, week=3) -> pd.DataFrame:
    """read_sql-shaped rows: (position, salary, projection, recent avg, actual, linked)."""
    return pd.DataFrame(
        [
            {
                "year": year, "week": week, "position": pos, "salary": salary,
                "proj_fpts": proj, "recent_avg": recent, "actual_dk_points": actual, "linked": linked,
            }
            for pos, salary, proj, recent, actual, linked in players
        ]
    )


NAN = float("nan")
RBS = [
    ("RB", 8500, 20.0, 18.0, 25.0, True),
    ("RB", 7000, 15.0, 16.0, 12.0, True),
    ("RB", 6000, 12.0, 9.0, 10.0, True),
    ("RB", 5000, 9.0, 11.0, 4.0, True),
    ("RB", 4000, 6.0, 5.0, 8.0, True),
]


def test_the_main_select_returns_what_the_report_reads():
    main = max(re.findall(r"SELECT(.*?)\bFROM\b", accuracy_db.ACCURACY_ROWS_QUERY.text, re.S), key=len)
    while "(" in main:
        main = re.sub(r"\([^()]*\)", "", main)
    names = [(c.rsplit(" AS ", 1)[1] if " AS " in c else c.split(".")[-1]).strip() for c in main.split(",")]
    assert names == [
        "year", "week", "player", "gsis_id", "nfl_team", "position", "salary",
        "proj_fpts", "recent_avg", "actual_dk_points", "linked",
    ]


def test_sources_are_compared_on_the_same_player_weeks():
    df = pd.concat([
        rows(*RBS),
        # No recent games (a rookie): projected, but there's nothing to compare.
        rows(("RB", 5500, 10.0, NAN, 14.0, True)),
        # Inactive, and one we couldn't match: counted, not scored.
        rows(("RB", 6500, 11.0, 10.0, NAN, True), ("RB", 4500, 7.0, 6.0, NAN, False)),
    ], ignore_index=True)

    report = build_report(df)

    assert report["coverage"] == {
        "considered": 8, "scored": 6, "no_stats": 1, "unlinked": 1, "no_baseline": 1, "evaluated": 5,
    }
    summary = report["summary"]
    assert summary["player_weeks"] == 5
    assert summary["metrics"]["projection"]["mae"] == pytest.approx((5 + 3 + 2 + 5 + 2) / 5)
    assert summary["metrics"]["recent_avg"]["mae"] == pytest.approx((7 + 4 + 1 + 7 + 3) / 5)
    # Five RBs in one week: the projection ordered them 25, 12, 10, 4, 8.
    assert summary["metrics"]["projection"]["rank_corr"] == pytest.approx(0.9)


def test_a_player_counts_when_either_source_rates_them():
    df = rows(
        ("WR", 3000, 2.0, 7.0, 3.0, True),  # only the baseline rated them
        ("WR", 3000, 2.0, 2.0, 30.0, True),  # nobody did: out
    )
    report = build_report(df, min_proj=5)
    assert report["coverage"]["evaluated"] == 1
    assert build_report(df, min_proj=0)["coverage"]["evaluated"] == 2


def test_the_position_table_ignores_the_position_filter():
    df = pd.concat([rows(*RBS), rows(("QB", 7000, 20.0, 22.0, 18.0, True))], ignore_index=True)

    report = build_report(df, position="QB")

    assert report["summary"]["player_weeks"] == 1
    assert [cell["position"] for cell in report["by_position"]] == ["QB", "RB"]
    assert [cell["player_weeks"] for cell in report["by_position"]] == [1, 5]
    # One QB can't be ranked; the five RBs can.
    assert report["by_position"][0]["metrics"]["projection"]["rank_corr"] is None
    assert report["by_position"][1]["metrics"]["projection"]["rank_corr"] == pytest.approx(0.9)


def test_weeks_seasons_and_salary_tiers():
    df = pd.concat([rows(*RBS, year=2024, week=5), rows(*RBS, year=2025, week=2)], ignore_index=True)

    report = build_report(df)
    assert report["seasons"] == [2025, 2024]
    assert [(c["year"], c["week"]) for c in report["by_week"]] == [(2024, 5), (2025, 2)]
    assert [(c["low"], c["high"], c["player_weeks"]) for c in report["by_salary"]] == [
        (4000, 6000, 4), (6000, 8000, 4), (8000, None, 2),
    ]
    assert all(c["metrics"]["projection"]["rank_corr"] is None for c in report["by_salary"])

    one_season = build_report(df, year=2024)
    assert one_season["summary"]["player_weeks"] == 5
    # The season list doesn't narrow with the filter.
    assert one_season["seasons"] == [2025, 2024]


def test_a_season_with_nothing_to_compare_is_empty_not_an_error():
    report = AccuracyResponse.model_validate(build_report(rows(*RBS), year=2019))
    assert report.summary.player_weeks == 0
    assert report.summary.metrics["projection"].mae is None
    assert report.by_week == [] and report.calibration["projection"] == []


@pytest.fixture
def served_rows(monkeypatch):
    monkeypatch.setattr(accuracy_db, "load_rows", lambda: rows(*RBS))


def test_route_returns_the_report(served_rows):
    response = client.get("/accuracy", params={"position": "RB", "min_proj": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["position"] == "RB" and body["min_proj"] == 0
    assert [s["key"] for s in body["sources"]] == ["projection", "recent_avg"]
    assert body["calibration"]["projection"][0]["player_weeks"] >= 1


def test_route_rejects_unknown_positions(served_rows):
    assert client.get("/accuracy", params={"position": "K"}).status_code == 422
    assert client.get("/accuracy", params={"min_proj": -1}).status_code == 422
