from datetime import datetime

from src.configs import log
from src.utils import get_current_week, get_salary_data


class SalaryScraper:
    def __init__(self):
        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_week = get_current_week()
        # adjusted year for FantasyPro's site
        self.fp_year = (
            self.current_year - 1
            if self.current_date.month in [1, 2]
            else self.current_year
        )

    def scrape(self, year: int | None = None, week: int | None = None) -> None:
        year = self.fp_year if year is None else year
        week = self.current_week if week is None else week

        df = get_salary_data(year=year)

        log.info("Saving salary data..")
        output_path = f"/app/data/salaries/dk_salary_{year}_w{week}.csv"
        df.to_csv(output_path, index=False)


if __name__ == "__main__":
    scraper = SalaryScraper()
    for year in range(2018, scraper.current_year + 1):
        log.info(f"Scraping salary data for year {year}..")
        scraper.scrape(year=year)
