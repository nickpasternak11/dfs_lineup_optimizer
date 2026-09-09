from src.configs import log
from src.salary_scraper import SalaryScraper

if __name__ == "__main__":
    log.info("Starting salary scraper..")
    scraper = SalaryScraper()

    for slate in ["Thu-Mon", "Wed-Mon", "Fri-Mon", "Sat-Mon", "Sat-Sun"]:
        df = scraper.scrape(slate)
        if not df.empty:
            scraper.save_to_csv(df)
            break
