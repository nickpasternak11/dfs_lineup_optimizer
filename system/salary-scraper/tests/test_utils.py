from datetime import date

import pandas as pd
import pytest
from src.utils import (
    EASTERN,
    get_current_week,
    get_salary_data,
    parse_currency,
    parse_kickoff,
)

# Wednesday of 2026 week 3; that week's Sunday is 2026-09-27.
WEDNESDAY = date(2026, 9, 23)


def test_parse_currency():
    parsed = parse_currency(pd.Series(["$7,400", "$3,000", "-", ""]))
    assert parsed.iloc[0] == 7400
    assert parsed.iloc[1] == 3000
    assert parsed.iloc[2:].isna().all()


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Thu 8:15 PM", (2026, 9, 24, 20, 15)),
        ("Sun 1:00 PM", (2026, 9, 27, 13, 0)),
        ("Sun 8:20PM", (2026, 9, 27, 20, 20)),
        ("Mon 8:15 PM", (2026, 9, 28, 20, 15)),
    ],
)
def test_parse_kickoff_places_the_day_in_the_week_of_the_reference(value, expected):
    kickoff = parse_kickoff(value, reference_date=WEDNESDAY)
    assert kickoff.tzinfo == EASTERN
    assert (kickoff.year, kickoff.month, kickoff.day, kickoff.hour, kickoff.minute) == expected


def test_parse_kickoff_on_sunday_uses_that_sunday():
    kickoff = parse_kickoff("Sun 1:00 PM", reference_date=date(2026, 9, 27))
    assert kickoff.date() == date(2026, 9, 27)


@pytest.mark.parametrize("value", ["TBD", "", "Sunday 1:00 PM", None, float("nan")])
def test_parse_kickoff_rejects_unparseable_values(value):
    assert parse_kickoff(value, reference_date=WEDNESDAY) is None


def test_get_salary_data_parses_the_salary_table(fake_fetch):
    calls = fake_fetch("salary_changes.html")

    df = get_salary_data(year=2025).set_index("player")

    assert calls[0][1] == {"year": 2025}
    assert list(df.index) == [
        "Josh Allen",
        "Patrick Mahomes II",
        "Green Bay Packers",
        "Jaxson Dart",
    ]

    allen = df.loc["Josh Allen"]
    assert (allen["team"], allen["position"], allen["opponent"]) == ("BUF", "QB", "MIA")
    assert bool(allen["home"]) is True
    assert (allen["salary"], allen["prev_salary"], allen["salary_change"]) == (7400, 7100, 300)

    packers = df.loc["Green Bay Packers"]
    assert (packers["team"], packers["position"], packers["opponent"]) == ("GB", "DST", "CLE")
    assert bool(packers["home"]) is False
    assert (packers["kickoff"].weekday(), packers["kickoff"].hour) == (6, 13)

    # No previous salary: the change is unknown, not zero.
    assert pd.isna(df.loc["Jaxson Dart", "prev_salary"])
    assert pd.isna(df.loc["Jaxson Dart", "salary_change"])


def test_get_salary_data_raises_when_the_page_has_no_table(fake_fetch):
    fake_fetch("empty.html")
    with pytest.raises(RuntimeError, match="No salary table"):
        get_salary_data(year=2025)


def test_get_current_week_reads_the_schedule_caption(fake_fetch):
    fake_fetch("schedule.html")
    assert get_current_week() == 3


def test_get_current_week_raises_instead_of_guessing(fake_fetch):
    # Regression: this used to fall back to week 1 and overwrite it.
    fake_fetch("empty.html")
    with pytest.raises(RuntimeError, match="current week"):
        get_current_week()
