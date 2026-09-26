import pandas as pd
from dfs_db import get_engine
from sqlalchemy import text


def get_latest_week(year: int | None = None) -> int:
    """Latest week that has a usable player pool.

    Queried against the view, not player_salaries: salaries land on Tuesday but
    projections arrive later, so keying off salaries alone can name a week the
    optimizer has no rows for.
    """
    if year is None:
        statement = text("SELECT max(week) FROM weekly_player_pool")
        params: dict = {}
    else:
        statement = text("SELECT max(week) FROM weekly_player_pool WHERE year = :year")
        params = {"year": year}

    with get_engine().connect() as connection:
        latest_week = connection.execute(statement, params).scalar()

    return int(latest_week) if latest_week is not None else 1


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a frame to JSON-safe records.

    Rows from weeks predating a column carry NaT/NA, which orjson refuses to
    serialise; they have to become None.
    """
    if df.empty:
        return []

    frame = df.copy()
    for column in frame.columns:
        if pd.api.types.is_datetime64_any_dtype(frame[column]):
            frame[column] = frame[column].dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    return frame.astype(object).where(pd.notna(frame), None).to_dict(orient="records")
