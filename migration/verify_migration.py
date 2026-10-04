"""Reconcile the CSV datasets against what landed in PostgreSQL.

Compares, per (year, week), the set of players in each CSV against the rows in
the corresponding table, and reports how many of those weeks survive the join
in weekly_player_pool -- which is what the API actually serves.

Exits non-zero if any CSV row is missing from the database.

Run it through the Makefile (`make verify-migration`) or directly inside the
image:

    python verify_migration.py
    python verify_migration.py --year 2025 --show-missing
"""

import argparse
import os
import sys

import pandas as pd
from configs import log
from dfs_db import get_engine
from migrate_csv_to_postgres import (
    DATASETS,
    DEFAULT_DATA_DIR,
    Dataset,
    coerce,
    discover,
)
from sqlalchemy import text


def csv_players(path: str) -> set[str]:
    df = pd.read_csv(path, skipinitialspace=True)
    if "player" not in df.columns:
        return set()
    df = coerce(df).dropna(subset=["player"])
    return set(df["player"].astype(str))


def db_players(dataset: Dataset, year: int, week: int) -> set[str]:
    statement = text(
        f"SELECT player FROM {dataset.model.__tablename__} "  # noqa: S608 - fixed set
        "WHERE year = :year AND week = :week"
    )
    with get_engine().connect() as connection:
        rows = connection.execute(statement, {"year": year, "week": week}).scalars()
        return set(rows)


def pool_count(year: int, week: int) -> int:
    statement = text(
        "SELECT count(*) FROM weekly_player_pool WHERE year = :year AND week = :week"
    )
    with get_engine().connect() as connection:
        return connection.execute(statement, {"year": year, "week": week}).scalar() or 0


def verify_dataset(
    dataset: Dataset,
    data_dir: str,
    year: int | None,
    week: int | None,
    show_missing: bool,
) -> int:
    log.info("=== %s ===", dataset.name)
    missing_total = 0

    for path, file_year, file_week in discover(dataset, data_dir, year, week):
        name = os.path.basename(path)
        in_csv = csv_players(path)
        in_db = db_players(dataset, file_year, file_week)

        missing = in_csv - in_db
        extra = in_db - in_csv
        missing_total += len(missing)

        status = "OK " if not missing else "GAP"
        log.info(
            "%s %s: csv=%s db=%s missing=%s db-only=%s",
            status,
            name,
            len(in_csv),
            len(in_db),
            len(missing),
            len(extra),
        )

        if missing and show_missing:
            for player in sorted(missing)[:20]:
                log.warning("    missing: %s", player)
            if len(missing) > 20:
                log.warning("    ... and %s more", len(missing) - 20)

    return missing_total


def verify_pool(data_dir: str, year: int | None, week: int | None) -> None:
    """Report how many rows the API would actually serve for each week."""
    log.info("=== weekly_player_pool ===")
    for _, file_year, file_week in discover(
        DATASETS["projections"], data_dir, year, week
    ):
        count = pool_count(file_year, file_week)
        status = "OK " if count else "GAP"
        log.info("%s %s w%s: %s row(s)", status, file_year, file_week, count)
        if not count:
            log.warning(
                "    no rows: projections for %s w%s have no matching salary rows",
                file_year,
                file_week,
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    parser.add_argument("--year", type=int)
    parser.add_argument("--week", type=int)
    parser.add_argument(
        "--show-missing", action="store_true", help="list the absent players"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not os.path.isdir(args.data_dir):
        log.error("Data directory not found: %s", args.data_dir)
        return 1

    missing = 0
    for dataset in DATASETS.values():
        missing += verify_dataset(
            dataset, args.data_dir, args.year, args.week, args.show_missing
        )

    verify_pool(args.data_dir, args.year, args.week)

    if missing:
        log.error("%s CSV row(s) are not in the database", missing)
        return 1

    log.info("All CSV rows are present in the database.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
