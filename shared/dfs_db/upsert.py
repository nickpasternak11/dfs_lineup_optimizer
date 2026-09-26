from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


def _clean(value: Any) -> Any:
    """Convert a pandas/numpy cell into something psycopg can bind.

    numpy scalars are not adaptable by the driver, and every pandas flavour of
    missing (NaN, NaT, pd.NA) has to collapse to None so the column goes NULL
    rather than becoming a literal 0 the way the CSV writer's fillna(0) did.
    """
    if isinstance(value, np.generic):
        value = value.item()
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        # Non-scalar (list, dict); pd.isna would return an array.
        pass
    return value


def upsert_dataframe(
    session: Session,
    model: type,
    df: pd.DataFrame,
    chunk_size: int = 500,
) -> int:
    """Upsert a DataFrame into `model`'s table, keyed on its primary key.

    Columns present on the table but absent from the DataFrame are left alone,
    so each scraper can write only the columns it owns.
    """
    if df.empty:
        return 0

    table = model.__table__
    table_columns = {column.name for column in table.columns}
    columns = [name for name in df.columns if name in table_columns]
    primary_key = [column.name for column in table.primary_key.columns]

    missing_key = set(primary_key) - set(columns)
    if missing_key:
        raise ValueError(f"DataFrame is missing primary key columns: {missing_key}")

    # A single INSERT cannot touch the same key twice, and the upstream tables
    # do occasionally list a player more than once.
    frame = df[columns].drop_duplicates(subset=primary_key, keep="last")
    frame = frame.dropna(subset=primary_key)

    updatable = [name for name in columns if name not in primary_key]
    records = [
        {key: _clean(value) for key, value in record.items()}
        for record in frame.to_dict(orient="records")
    ]

    for start in range(0, len(records), chunk_size):
        chunk = records[start : start + chunk_size]
        statement = pg_insert(table).values(chunk)
        set_ = {name: statement.excluded[name] for name in updatable}
        if "scraped_at" in table_columns:
            set_["scraped_at"] = func.now()
        session.execute(
            statement.on_conflict_do_update(index_elements=primary_key, set_=set_)
        )

    return len(records)


def replace_weeks(session: Session, model: type, df: pd.DataFrame) -> int:
    """Replace every (year, week) present in `df` with exactly its rows.

    A scrape is a complete snapshot of its week, so rows the new snapshot no
    longer contains -- a player dropped from the rankings, or the same player
    under an older spelling ("Packers" vs "Green Bay Packers") -- must go,
    which an upsert keyed on player name cannot do. Runs inside the caller's
    transaction, so readers never see a half-replaced week.
    """
    if df.empty:
        return 0

    table = model.__table__
    for year, week in df[["year", "week"]].drop_duplicates().itertuples(index=False):
        session.execute(
            delete(table).where(table.c.year == int(year), table.c.week == int(week))
        )
    return upsert_dataframe(session, model, df)
