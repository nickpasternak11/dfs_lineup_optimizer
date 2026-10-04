from contextlib import contextmanager

import pandas as pd
import pytest
import src.salary_scraper as salary_scraper
from dfs_db.upsert import DEFAULT_MIN_RATIO
from src.salary_scraper import SalaryScraper


@pytest.fixture
def scraper(monkeypatch):
    """A scraper whose network and database calls are captured, not made."""
    saved = {}

    @contextmanager
    def fake_session_scope():
        yield "session"

    def fake_replace_weeks(session, model, df, min_ratio):
        saved.update(model=model, df=df.copy(), min_ratio=min_ratio)
        return len(df)

    salaries = pd.DataFrame(
        {
            "player": ["Josh Allen", "Green Bay Packers"],
            "position": ["QB", "DST"],
            "team": ["BUF", "GB"],
            "opponent": ["MIA", "CLE"],
            "home": [True, False],
            "kickoff": pd.to_datetime(["2026-09-25T00:15Z", "2026-09-27T17:00Z"]),
            "salary": [7400.0, 3700.0],
            "prev_salary": [7100.0, float("nan")],
            "salary_change": [300.0, float("nan")],
        }
    )

    monkeypatch.setattr(salary_scraper, "get_current_week", lambda: 3)
    monkeypatch.setattr(salary_scraper, "get_salary_data", lambda year: salaries.copy())
    monkeypatch.setattr(salary_scraper, "session_scope", fake_session_scope)
    monkeypatch.setattr(salary_scraper, "replace_weeks", fake_replace_weeks)

    instance = SalaryScraper()
    instance.saved = saved
    return instance


def test_rows_are_filed_under_the_current_week(scraper):
    scraper.scrape(year=2018)
    df = scraper.saved["df"]
    assert set(df["week"]) == {3}
    assert set(df["year"]) == {2018}


def test_past_seasons_get_no_kickoff(scraper):
    # The page only gives a weekday and time; placed in the current calendar
    # week, those dates are fabricated for any past season.
    scraper.scrape(year=scraper.fp_year - 3)
    assert scraper.saved["df"]["kickoff"].isna().all()


def test_the_live_season_keeps_its_kickoffs(scraper):
    scraper.scrape(year=scraper.fp_year)
    assert scraper.saved["df"]["kickoff"].notna().all()


def test_salaries_are_whole_dollars_with_missing_values_kept(scraper):
    scraper.scrape(year=scraper.fp_year)
    df = scraper.saved["df"]
    assert str(df["salary"].dtype) == "Int64"
    assert df["salary"].tolist() == [7400, 3700]
    assert pd.isna(df["salary_change"].iloc[1])


def test_shrink_guard_is_on_by_default(scraper):
    scraper.scrape()
    assert scraper.saved["min_ratio"] == DEFAULT_MIN_RATIO


def test_allow_shrink_disables_the_guard(scraper):
    scraper.scrape(allow_shrink=True)
    assert scraper.saved["min_ratio"] == 0


def test_empty_salary_table_fails_instead_of_saving(scraper, monkeypatch):
    monkeypatch.setattr(salary_scraper, "get_salary_data", lambda year: pd.DataFrame())
    with pytest.raises(RuntimeError, match="empty"):
        scraper.scrape()
    assert scraper.saved == {}
