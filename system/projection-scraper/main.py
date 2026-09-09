from src.configs import log
from src.projection_scraper import ProjectionScraper

if __name__ == "__main__":
    log.info("Starting projection scraper..")
    scraper = ProjectionScraper()
    scraper.scrape()
