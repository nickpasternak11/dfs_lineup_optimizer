import re
from datetime import date, datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pandas as pd
from dfs_common.fantasypros import fetch

PLAYER_PATTERN = re.compile(
    r"^(?P<player>.*?)\s*\((?P<team>.*?)\s*-\s*(?P<position>.*?)\)"
)
KICKOFF_PATTERN = re.compile(
    r"^\s*(?P<day>Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)\s*$",
    re.IGNORECASE,
)
EASTERN = ZoneInfo("America/New_York")
DAY_OFFSETS = {
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": -3,
    "fri": -2,
    "sat": -1,
}


def parse_currency(values: pd.Series) -> pd.Series:
    return pd.to_numeric(
        values.astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce",
    )


def parse_kickoff(value: str, reference_date: date | None = None) -> datetime | None:
    if not isinstance(value, str):
        return None

    match = KICKOFF_PATTERN.match(value)
    if not match:
        return None

    reference_date = reference_date or datetime.now(EASTERN).date()
    sunday = reference_date + timedelta(days=(6 - reference_date.weekday()) % 7)
    kickoff_date = sunday + timedelta(days=DAY_OFFSETS[match.group("day").lower()])
    kickoff_time = (
        datetime.strptime(match.group("time").replace(" ", "").upper(), "%I:%M%p")
        .replace(tzinfo=EASTERN)
        .timetz()
    )
    return datetime.combine(kickoff_date, kickoff_time)


def get_salary_data(year: int) -> pd.DataFrame:
    url = "https://www.fantasypros.com/daily-fantasy/nfl/draftkings-salary-changes.php"
    params = {"year": year}
    r = fetch(url, params=params)

    try:
        df = pd.read_html(StringIO(r.text))[0]
    except ValueError as error:
        raise RuntimeError(f"No salary table on the page for year={year}") from error

    df[["player", "team", "position"]] = df["Player"].str.extract(PLAYER_PATTERN)
    df["opponent"] = df["Opp"].astype("string").str.replace("@", "", regex=False)
    df["home"] = ~df["Opp"].astype("string").str.startswith("@", na=False)
    df["salary"] = parse_currency(df["This Week"])
    df["prev_salary"] = parse_currency(df["Last Week"])
    df["salary_change"] = df["salary"] - df["prev_salary"]
    df["kickoff"] = df["Kickoff"].map(parse_kickoff)

    return df[
        [
            "player",
            "position",
            "team",
            "opponent",
            "home",
            "kickoff",
            "salary",
            "prev_salary",
            "salary_change",
        ]
    ]
