import argparse
import sys

from src.configs import log
from src.projection_scraper import ProjectionScraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the FantasyPros projection scraper."
    )
    parser.add_argument("--year", type=int, help="season year (default: current)")
    parser.add_argument("--week", type=int, help="week number (default: current)")
    parser.add_argument(
        "--start-year",
        type=int,
        help="scrape --week (default: current) for every season from "
        "--start-year through --end-year",
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
    scraper = ProjectionScraper()

    if args.start_year is None and args.end_year is None:
        log.info("Starting projection scraper..")
        scraper.scrape(year=args.year, week=args.week, allow_shrink=args.allow_shrink)
        sys.exit(0)

    if args.start_year is None:
        raise SystemExit("--end-year requires --start-year")
    end_year = scraper.fp_year - 1 if args.end_year is None else args.end_year
    week = scraper.current_week if args.week is None else args.week

    failed = []
    for year in range(args.start_year, end_year + 1):
        log.info("Scraping projection data for year=%s week=%s..", year, week)
        try:
            scraper.scrape(year=year, week=week, allow_shrink=args.allow_shrink)
        except Exception:  # noqa: BLE001 - one bad season shouldn't stop the rest
            log.exception("Projection scrape failed for year=%s", year)
            failed.append(year)

    if failed:
        log.error("Projection scrape failed for years: %s", failed)
        sys.exit(1)
