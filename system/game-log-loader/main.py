import argparse
import sys

from dfs_common.season import current_season_year
from src.configs import FIRST_SEASON, log
from src.loader import load_player_ids, load_season, refresh_links


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load nflverse games and weekly game logs, with DraftKings points."
    )
    parser.add_argument("--year", type=int, help="season to load (default: current)")
    parser.add_argument(
        "--start-year",
        type=int,
        help=f"load every season from --start-year (>= {FIRST_SEASON}) through --end-year",
    )
    parser.add_argument("--end-year", type=int, help="with --start-year (default: current)")
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="replace a season even if the new data has far fewer rows than "
        "what is stored (normally refused as a likely partial download)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    current = current_season_year()

    if args.start_year is None:
        if args.end_year is not None:
            raise SystemExit("--end-year requires --start-year")
        years = [current if args.year is None else args.year]
    else:
        if args.start_year < FIRST_SEASON:
            raise SystemExit(f"nflverse weekly stats start in {FIRST_SEASON}")
        years = list(range(args.start_year, (args.end_year or current) + 1))

    # The id map isn't per season; refresh it once per run.
    load_player_ids(allow_shrink=args.allow_shrink)

    failed = []
    for year in years:
        try:
            load_season(year, allow_shrink=args.allow_shrink)
        except Exception:  # noqa: BLE001 - one bad season shouldn't stop the rest
            log.exception("Game log load failed for %s", year)
            failed.append(year)

    # Even after a failed season: the others' new games still need linking.
    try:
        refresh_links()
    except Exception:  # noqa: BLE001
        log.exception("Refreshing pool player links failed")
        failed.append("links")

    if failed:
        log.error("Game log load failed for: %s", failed)
        sys.exit(1)
