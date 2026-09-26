import argparse

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
        help="with --end-year, scrape the current week for every season from "
        "--start-year through --end-year",
    )
    parser.add_argument("--end-year", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scraper = SalaryScraper()

    if args.start_year is not None or args.end_year is not None:
        if args.start_year is None or args.end_year is None:
            raise SystemExit("--start-year and --end-year must be used together")
        for year in range(args.start_year, args.end_year + 1):
            log.info(
                "Scraping salary data for year=%s week=%s..",
                year,
                scraper.current_week,
            )
            scraper.scrape(year=year)
    else:
        log.info("Starting salary scraper..")
        scraper.scrape(year=args.year)
