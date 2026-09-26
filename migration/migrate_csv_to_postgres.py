"""Migrate the historical CSV datasets into PostgreSQL.

Every write is an upsert keyed on (year, week, player), so the script is
idempotent and safe to re-run after a partial failure.

The filename is authoritative for year and week. Older files predate several
columns (home, kickoff, salary_change, injury_status, injury_type); those are
left NULL rather than invented, and get filled when the scrapers next cover
that week.

Files whose rows come from a different season than their filename claims are
skipped, not imported -- see load_frame for why.

Run it through the Makefile (`make migrate`, `make migrate-dry-run`) or
directly inside the image:

    python migrate_csv_to_postgres.py --dry-run
    python migrate_csv_to_postgres.py --year 2025
    python migrate_csv_to_postgres.py --dataset salaries --year 2024 --week 3
"""

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass, field

import pandas as pd
from configs import log
from dfs_db import PlayerProjection, PlayerSalary, session_scope, upsert_dataframe

DEFAULT_DATA_DIR = os.getenv("DATA_DIR", "/app/data")

INT_COLUMNS = ["salary", "prev_salary", "salary_change", "rank", "min_rank", "max_rank"]
FLOAT_COLUMNS = ["avg_fpts", "proj_fpts", "avg_rank", "std_rank"]
BOOL_COLUMNS = ["home"]
DATETIME_COLUMNS = ["kickoff"]

KEY_COLUMNS = ["year", "week", "player"]


@dataclass
class Dataset:
    name: str
    subdir: str
    pattern: re.Pattern
    model: type
    # Columns the current scrapers emit. Anything missing from an older file is
    # reported once and left NULL.
    expected: list[str]


@dataclass
class Stats:
    files: int = 0
    rows_read: int = 0
    rows_written: int = 0
    dropped_no_player: int = 0
    duplicates: int = 0
    skipped: int = 0
    bogus_kickoffs: int = 0
    errors: list[str] = field(default_factory=list)


class SkipFile(Exception):
    """Raised when a file's contents contradict its filename."""


DATASETS = {
    "salaries": Dataset(
        name="salaries",
        subdir="salaries",
        pattern=re.compile(r"^dk_salary_(?P<year>\d{4})_w(?P<week>\d{1,2})\.csv$"),
        model=PlayerSalary,
        expected=[
            "player",
            "position",
            "team",
            "opponent",
            "home",
            "kickoff",
            "salary",
            "prev_salary",
            "salary_change",
        ],
    ),
    "projections": Dataset(
        name="projections",
        subdir="projections",
        pattern=re.compile(r"^fp_projection_(?P<year>\d{4})_w(?P<week>\d{1,2})\.csv$"),
        model=PlayerProjection,
        expected=[
            "player",
            "position",
            "grade",
            "rank",
            "avg_fpts",
            "proj_fpts",
            "injury_status",
            "injury_type",
        ],
    ),
}


def discover(dataset: Dataset, data_dir: str, year: int | None, week: int | None):
    """Yield (path, year, week) for files matching the dataset and filters."""
    paths = sorted(glob.glob(os.path.join(data_dir, dataset.subdir, "*.csv")))
    for path in paths:
        match = dataset.pattern.match(os.path.basename(path))
        if not match:
            log.warning("Skipping unrecognised filename: %s", os.path.basename(path))
            continue

        file_year = int(match.group("year"))
        file_week = int(match.group("week"))
        if year is not None and file_year != year:
            continue
        if week is not None and file_week != week:
            continue

        yield path, file_year, file_week


def coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise CSV text into the types the table expects."""
    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].astype("string").str.strip()
        # Empty strings are missing values, not empty text.
        df[column] = df[column].replace("", pd.NA)

    for column in INT_COLUMNS:
        if column in df.columns:
            df[column] = (
                pd.to_numeric(df[column], errors="coerce").round().astype("Int64")
            )

    for column in FLOAT_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in BOOL_COLUMNS:
        if column in df.columns and df[column].dtype != bool:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
                .str.lower()
                .map({"true": True, "false": False, "1": True, "0": False})
            )

    for column in DATETIME_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)

    return df


def load_frame(
    path: str,
    year: int,
    week: int,
    dataset: Dataset,
    stats: Stats,
    allow_year_mismatch: bool,
) -> pd.DataFrame:
    name = os.path.basename(path)
    df = pd.read_csv(path, skipinitialspace=True)
    stats.rows_read += len(df)

    missing = [column for column in dataset.expected if column not in df.columns]
    if missing:
        log.info("%s: no %s column(s); leaving NULL", name, missing)

    if "player" not in df.columns:
        raise ValueError("file has no 'player' column")

    # A `year` column disagreeing with the filename means the file was written
    # by a backfill run that fetched the CURRENT season's rankings and joined
    # them onto that season's salaries. The rows are a blend of two seasons and
    # are not the history the filename claims.
    if "year" in df.columns:
        years = df["year"].dropna().astype(int)
        mismatched = years.ne(year).sum()
        if mismatched and not allow_year_mismatch:
            found = sorted(years[years.ne(year)].unique())
            raise SkipFile(
                f"{mismatched} of {len(df)} row(s) are from {found}, not {year}"
            )
        if mismatched:
            log.warning("%s: %s row(s) have year != %s", name, mismatched, year)

    df = coerce(df)
    df["year"] = year
    df["week"] = week

    # parse_kickoff resolves weekday names against the date of the scrape, so a
    # historical week gets stamped with kickoffs from whenever it was scraped.
    # A season runs August of its year through February of the next; a
    # calendar-year check alone would accept September of Y+1.
    if "kickoff" in df.columns:
        season_start = pd.Timestamp(year=year, month=8, day=1, tz="UTC")
        season_end = pd.Timestamp(year=year + 1, month=3, day=1, tz="UTC")
        kickoff = df["kickoff"]
        bogus = kickoff.notna() & ((kickoff < season_start) | (kickoff >= season_end))
        count = int(bogus.sum())
        if count:
            log.warning(
                "%s: nulling %s kickoff(s) outside season %s", name, count, year
            )
            df.loc[bogus, "kickoff"] = pd.NaT
            stats.bogus_kickoffs += count

    before = len(df)
    df = df.dropna(subset=["player"])
    stats.dropped_no_player += before - len(df)

    before = len(df)
    df = df.drop_duplicates(subset=KEY_COLUMNS, keep="last")
    stats.duplicates += before - len(df)

    return df


def migrate_dataset(
    dataset: Dataset,
    data_dir: str,
    year: int | None,
    week: int | None,
    dry_run: bool,
    fail_fast: bool,
    allow_year_mismatch: bool,
) -> Stats:
    stats = Stats()
    log.info("=== %s ===", dataset.name)

    for path, file_year, file_week in discover(dataset, data_dir, year, week):
        name = os.path.basename(path)
        stats.files += 1

        try:
            df = load_frame(
                path, file_year, file_week, dataset, stats, allow_year_mismatch
            )
        except SkipFile as reason:
            log.warning("SKIP %s: %s", name, reason)
            stats.skipped += 1
            continue
        except (ValueError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            message = f"{name}: {error}"
            log.error("Failed to parse %s", message)
            stats.errors.append(message)
            if fail_fast:
                break
            continue

        if df.empty:
            log.warning("%s: no usable rows", name)
            continue

        if dry_run:
            log.info("%s: would write %s rows", name, len(df))
            stats.rows_written += len(df)
            continue

        try:
            with session_scope() as session:
                written = upsert_dataframe(session, dataset.model, df)
        except Exception as error:  # noqa: BLE001 - reported and surfaced below
            message = f"{name}: {error}"
            log.error("Failed to write %s", message)
            stats.errors.append(message)
            if fail_fast:
                break
            continue

        stats.rows_written += written
        log.info("%s: wrote %s rows", name, written)

    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    parser.add_argument("--dataset", choices=["all", *DATASETS], default="all")
    parser.add_argument("--year", type=int, help="only migrate this season year")
    parser.add_argument("--week", type=int, help="only migrate this week")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse and validate without writing (does not check DB constraints)",
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="stop at the first failing file"
    )
    parser.add_argument(
        "--allow-year-mismatch",
        action="store_true",
        help="import files whose rows come from a different season than their "
        "filename claims (they are a blend of two seasons)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not os.path.isdir(args.data_dir):
        log.error("Data directory not found: %s", args.data_dir)
        return 1

    # Salaries first: the weekly_player_pool view only surfaces a projection
    # once its matching salary row exists.
    names = list(DATASETS) if args.dataset == "all" else [args.dataset]

    totals = Stats()
    for name in names:
        stats = migrate_dataset(
            DATASETS[name],
            args.data_dir,
            args.year,
            args.week,
            args.dry_run,
            args.fail_fast,
            args.allow_year_mismatch,
        )
        totals.files += stats.files
        totals.rows_read += stats.rows_read
        totals.rows_written += stats.rows_written
        totals.dropped_no_player += stats.dropped_no_player
        totals.duplicates += stats.duplicates
        totals.skipped += stats.skipped
        totals.bogus_kickoffs += stats.bogus_kickoffs
        totals.errors.extend(stats.errors)

    verb = "would write" if args.dry_run else "wrote"
    log.info(
        "Done: %s file(s), read %s row(s), %s %s row(s), "
        "dropped %s without a player, collapsed %s duplicate key(s)",
        totals.files,
        totals.rows_read,
        verb,
        totals.rows_written,
        totals.dropped_no_player,
        totals.duplicates,
    )
    if totals.skipped:
        log.warning(
            "Skipped %s file(s) whose rows are from a different season than "
            "their filename; re-run with --allow-year-mismatch to import them",
            totals.skipped,
        )
    if totals.bogus_kickoffs:
        log.warning("Nulled %s fabricated kickoff(s)", totals.bogus_kickoffs)

    if totals.errors:
        log.error("%s file(s) failed:", len(totals.errors))
        for message in totals.errors:
            log.error("  %s", message)
        return 1

    if totals.files == 0:
        log.warning("No matching CSV files found under %s", args.data_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
