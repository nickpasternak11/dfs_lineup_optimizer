import argparse
import sys

from src.configs import log
from src.salary_scraper import SalaryScraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the DraftKings salary scraper. The source only serves "
        "the current NFL week, so there is no --week: past seasons can be "
        "backfilled only for the week currently in progress."
    )
    parser.add_argument("--year", type=int, help="season year (default: current)")
    parser.add_argument(
        "--start-year",
        type=int,
        help="scrape the current week for every season from --start-year "
        "through --end-year",
    )
    parser.add_argument(
        "--end-year", type=int, help="with --start-year (default: last season)"
    )
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="replace a week even if the new scrape has far fewer rows than "
        "what is stored (normally refused as a likely partial scrape)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scraper = SalaryScraper()

    if args.start_year is None and args.end_year is None:
        log.info("Starting salary scraper..")
        scraper.scrape(year=args.year, allow_shrink=args.allow_shrink)
        sys.exit(0)

    if args.start_year is None:
        raise SystemExit("--end-year requires --start-year")
    end_year = scraper.fp_year - 1 if args.end_year is None else args.end_year

    failed = []
    for year in range(args.start_year, end_year + 1):
        log.info(
            "Scraping salary data for year=%s week=%s..", year, scraper.current_week
        )
        try:
            scraper.scrape(year=year, allow_shrink=args.allow_shrink)
        except Exception:  # noqa: BLE001 - one bad season shouldn't stop the rest
            log.exception("Salary scrape failed for year=%s", year)
            failed.append(year)

    if failed:
        log.error("Salary scrape failed for years: %s", failed)
        sys.exit(1)
