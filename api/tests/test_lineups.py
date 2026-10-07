from datetime import datetime, timezone

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.application import application
from app.db import lineups as lineups_db
from app.helpers.lineups import build_review
from app.models.responses.lineups import LineupReviewResponse

client = TestClient(application)
SAVED = pd.Timestamp("2026-10-11T13:00:00Z")


def saved_lineup(source, strategy, actuals, projection=10.0, phase="initial", saved=SAVED):
    return [
        {"generated_at": saved, "phase": phase, "source": source, "strategy": strategy, "slot": i,
         "player": f"{source}-{phase}-{i}",
         "position": "WR", "team": "BUF", "salary": 5000, "projection": projection, "actual": actual}
        for i, actual in enumerate(actuals)
    ]


@pytest.fixture
def week(monkeypatch):
    rows = (
        saved_lineup("model", "projection", [12.0] * 8 + [None])  # one didn't play: counts 0
        + saved_lineup("fantasypros", "blend_90_10", [9.0] * 9)
        + saved_lineup("fantasypros", "projection", [10.0] * 9)
    )
    best = pd.DataFrame({
        "player": [f"best-{i}" for i in range(9)], "position": "WR", "team": "BUF",
        "salary": 5000, "actual": [20.0] * 9,
    })
    monkeypatch.setattr(lineups_db, "snapshot_weeks", lambda: [{"year": 2026, "week": 6}])
    monkeypatch.setattr(lineups_db, "load_snapshot", lambda year, week: pd.DataFrame(rows))
    monkeypatch.setattr(lineups_db, "unfinished_games", lambda year, week, since: 0)
    monkeypatch.setattr(lineups_db, "best_lineup", lambda year, week, since: best)


def test_the_review_scores_each_saved_lineup_against_the_best(week):
    review = build_review()

    assert (review["year"], review["week"], review["complete"]) == (2026, 6, True)
    # FantasyPros first, then our model; within each, projection then blends.
    assert [(l["source"], l["strategy"]) for l in review["lineups"]] == [
        ("fantasypros", "projection"), ("fantasypros", "blend_90_10"), ("model", "projection"),
    ]
    model = review["lineups"][2]
    assert (model["projected"], model["actual"]) == (90.0, 96.0)
    assert model["players"][8]["actual"] is None
    assert review["best"]["actual"] == 180.0
    assert review["season"] == [{
        "week": 6, "complete": True, "best": 180.0,
        "lineups": [
            {"phase": "initial", "source": "fantasypros", "strategy": "projection", "projected": 90.0, "actual": 90.0},
            {"phase": "initial", "source": "fantasypros", "strategy": "blend_90_10", "projected": 90.0, "actual": 81.0},
            {"phase": "initial", "source": "model", "strategy": "projection", "projected": 90.0, "actual": 96.0},
        ],
    }]
    LineupReviewResponse.model_validate(review)


def test_no_saved_lineups_yet(monkeypatch):
    monkeypatch.setattr(lineups_db, "snapshot_weeks", lambda: [])
    review = LineupReviewResponse.model_validate(build_review())
    assert review.weeks == [] and review.lineups == [] and review.best is None


def test_the_best_lineup_uses_actual_points_from_players_still_to_play(monkeypatch):
    # Thursday's game was before the lineups were saved, so its 40-point WR
    # isn't eligible; an inactive player scored nothing.
    players = []
    for i, (position, actual, kickoff) in enumerate(
        [("QB", 25.0, "sun")] + [("RB", 15.0 - i, "sun") for i in range(3)]
        + [("WR", 18.0 - i, "sun") for i in range(4)] + [("WR", 40.0, "thu"), ("WR", None, "sun")]
        + [("TE", 9.0, "sun"), ("DST", 7.0, "sun")]
    ):
        players.append({
            "player": f"{position}{i}", "position": position, "team": "T", "salary": 5000,
            "proj_fpts": 10.0, "avg_fpts": 10.0, "actual_dk_points": actual,
            "kickoff": pd.Timestamp("2026-10-09T00:15:00Z" if kickoff == "thu" else "2026-10-11T17:00:00Z"),
        })
    monkeypatch.setattr(lineups_db, "load_player_pool", lambda year, week: pd.DataFrame(players))

    best = lineups_db._solve_best(2026, 6, SAVED.to_pydatetime())

    assert "WR8" not in set(best.player)  # the Thursday receiver
    # QB 25, RBs 15 and 14, WRs 18, 17 and 16, FLEX the 15-point WR, TE 9, DST 7.
    assert best.actual.sum() == pytest.approx(136.0)


def test_route(week):
    response = client.get("/lineups/review", params={"year": 2026, "week": 6})
    assert response.status_code == 200
    assert response.json()["best"]["actual"] == 180.0


def test_the_review_opens_on_the_newest_finished_week(week, monkeypatch):
    monkeypatch.setattr(lineups_db, "snapshot_weeks", lambda: [{"year": 2026, "week": 7}, {"year": 2026, "week": 6}])
    monkeypatch.setattr(lineups_db, "unfinished_games", lambda year, week, since: 16 if week == 7 else 0)
    review = build_review()
    assert (review["week"], review["complete"]) == (6, True)
    assert [(w["week"], w["complete"]) for w in review["season"]] == [(6, True), (7, False)]


def test_no_best_lineup_before_there_are_results(monkeypatch):
    pool = pd.DataFrame({
        "player": ["A"], "position": "QB", "team": "T", "salary": 5000, "proj_fpts": 10.0,
        "avg_fpts": 10.0, "actual_dk_points": [None], "kickoff": [pd.Timestamp("2026-10-11T17:00:00Z")],
    })
    monkeypatch.setattr(lineups_db, "load_player_pool", lambda year, week: pool)
    with pytest.raises(ValueError, match="No results yet"):
        lineups_db._solve_best(2026, 7, SAVED.to_pydatetime())


def test_the_late_swap_sits_beside_its_lineup_and_shares_its_slate(monkeypatch):
    swapped_at = pd.Timestamp("2026-10-11T15:50:00Z")
    rows = (
        saved_lineup("model", "projection", [12.0] * 9)
        + saved_lineup("model", "projection", [14.0] * 9, phase="late_swap", saved=swapped_at)
    )
    slates = []
    monkeypatch.setattr(lineups_db, "snapshot_weeks", lambda: [{"year": 2026, "week": 6}])
    monkeypatch.setattr(lineups_db, "load_snapshot", lambda year, week: pd.DataFrame(rows))
    monkeypatch.setattr(lineups_db, "unfinished_games", lambda year, week, since: 0)

    def best(year, week, since):
        slates.append(since)
        return pd.DataFrame({"player": ["x"], "position": "QB", "team": "T", "salary": 5000, "actual": [150.0]})

    monkeypatch.setattr(lineups_db, "best_lineup", best)
    review = build_review()

    assert [(l["phase"], l["actual"]) for l in review["lineups"]] == [("initial", 108.0), ("late_swap", 126.0)]
    assert review["swapped_at"] == swapped_at.to_pydatetime()
    # The hindsight best is the whole slate's: from the first save, not the swap.
    assert set(slates) == {SAVED.to_pydatetime()}
    LineupReviewResponse.model_validate(review)
