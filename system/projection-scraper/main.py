import argparse

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
        help="with --end-year and --week, scrape that week for every season "
        "from --start-year through --end-year",
    )
    parser.add_argument("--end-year", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    scraper = ProjectionScraper()

    if args.start_year is not None or args.end_year is not None:
        if args.week is None or args.start_year is None or args.end_year is None:
            raise SystemExit("--start-year/--end-year require each other and --week")
        for year in range(args.start_year, args.end_year + 1):
            log.info("Scraping projection data for year=%s week=%s..", year, args.week)
            scraper.scrape(year=year, week=args.week)
    else:
        log.info("Starting projection scraper..")
        scraper.scrape(year=args.year, week=args.week)
