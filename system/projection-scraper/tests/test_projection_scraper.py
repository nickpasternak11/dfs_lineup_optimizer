from contextlib import contextmanager

import pandas as pd
import pytest
import src.projection_scraper as projection_scraper
from src.projection_scraper import POSITIONS, ProjectionScraper


def rankings_for(position: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player": [f"{position} One", f"{position} Two"],
            "position": [position, position],
            "rank": [1, 2],
            "grade": ["A", "B"],
            "proj_fpts": [20.0, 15.0],
        }
    )


@pytest.fixture
def scraper(monkeypatch):
    """A scraper whose network and database calls are captured, not made."""
    captured = {"injury_calls": []}

    @contextmanager
    def fake_session_scope():
        yield "session"

    def fake_replace_weeks(session, model, df, min_ratio):
        captured.update(df=df.copy(), min_ratio=min_ratio)
        return len(df)

    def fake_injuries(year, week):
        captured["injury_calls"].append((year, week))
        return pd.DataFrame(
            {"player": ["QB One"], "injury_status": ["Questionable"], "injury_type": ["Ankle"]}
        )

    monkeypatch.setattr(projection_scraper, "get_current_week", lambda: 3)
    monkeypatch.setattr(projection_scraper, "get_weekly_rankings", lambda pos, y, w: rankings_for(pos))
    monkeypatch.setattr(
        projection_scraper,
        "get_stats",
        lambda pos, y, weeks: pd.DataFrame({"player": [f"{pos} One"], "avg_fpts": [18.0]}),
    )
    monkeypatch.setattr(projection_scraper, "get_player_injuries", fake_injuries)
    monkeypatch.setattr(projection_scraper, "session_scope", fake_session_scope)
    monkeypatch.setattr(projection_scraper, "replace_weeks", fake_replace_weeks)

    instance = ProjectionScraper()
    instance.captured = captured
    return instance


def test_every_position_is_saved_for_the_target_week(scraper):
    scraper.scrape(year=2018, week=3)
    df = scraper.captured["df"]
    assert set(df["position"]) == set(POSITIONS)
    assert set(df["year"]) == {2018}
    assert set(df["week"]) == {3}


def test_players_without_recent_stats_keep_a_null_average(scraper):
    scraper.scrape(year=2018, week=3)
    df = scraper.captured["df"].set_index("player")
    assert df.loc["QB One", "avg_fpts"] == 18.0
    assert pd.isna(df.loc["QB Two", "avg_fpts"])


def test_injuries_come_from_the_target_week(scraper):
    scraper.scrape(year=2018, week=3)
    df = scraper.captured["df"].set_index("player")

    assert scraper.captured["injury_calls"] == [(2018, 3)]
    assert tuple(df.loc["QB One", ["injury_status", "injury_type"]]) == ("Questionable", "Ankle")
    # Absent from the report: NULL, not "Healthy" or 0.
    assert pd.isna(df.loc["QB Two", "injury_status"])


def test_an_empty_position_fails_the_whole_scrape(scraper, monkeypatch):
    # Saving the other four positions would replace a complete week.
    monkeypatch.setattr(
        projection_scraper,
        "get_weekly_rankings",
        lambda pos, y, w: pd.DataFrame() if pos == "DST" else rankings_for(pos),
    )
    with pytest.raises(RuntimeError, match="No DST rankings"):
        scraper.scrape(year=2018, week=3)
    assert "df" not in scraper.captured


def test_defaults_to_the_current_season_and_week(scraper):
    scraper.scrape()
    df = scraper.captured["df"]
    assert set(df["year"]) == {scraper.fp_year}
    assert set(df["week"]) == {3}


def test_allow_shrink_disables_the_guard(scraper):
    scraper.scrape(year=2018, week=3, allow_shrink=True)
    assert scraper.captured["min_ratio"] == 0
