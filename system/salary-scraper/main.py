from src.configs import log
from src.salary_scraper import SalaryScraper

if __name__ == "__main__":
    log.info("Starting salary scraper..")
    scraper = SalaryScraper()
    scraper.scrape()
