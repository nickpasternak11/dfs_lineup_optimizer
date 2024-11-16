import os
from datetime import datetime, timedelta
from io import StringIO
from time import sleep

import pandas as pd
import pytz
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from utils import get_current_week


class SalaryScraper:
    def __init__(self, on_demand: bool = False):
        self.on_demand = on_demand
        self.url = "https://draftdime.com/nfl-projections"
        self.current_year = datetime.now().year
        self.current_week = get_current_week(year=self.current_year)
        self.check_webdriver_container()

    @staticmethod
    def check_webdriver_container():
        # wait until webdriver container is up
        print("Waiting for selenium webdriver..")
        while True:
            try:
                requests.get("http://selenium-web-driver:4444/wd/hub")
                break
            except:
                continue
        print("Webdriver is up!\n")

    def scrape(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        print("Scraping salary data..")
        with webdriver.Remote(command_executor="http://selenium-web-driver:4444/wd/hub", options=options) as browser:
            browser.get(self.url)
            sleep(1)
            site_select = Select(browser.find_element(by=By.ID, value="site-id"))
            sleep(1)
            site_select.select_by_visible_text("DraftKings")
            sleep(3)
            modal = browser.find_element(by=By.ID, value="sign-up-modal")
            sleep(1)
            modal.find_element(by=By.TAG_NAME, value="button").click()
            sleep(3)
            slate_select = Select(browser.find_element(by=By.ID, value="slate-select"))
            sleep(2)
            slate_select.select_by_visible_text("Thu-Mon")
            sleep(3)
            html = browser.page_source
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", id="prj-main-table")

        salary_df = pd.io.html.read_html(StringIO(str(table)))[0].iloc[1:, :6]
        salary_df.columns = ["player", "extra", "position", "team", "opponent", "salary"]
        salary_df = salary_df.drop(columns=["extra"])
        salary_df["opponent"] = salary_df.opponent.str.replace("@", "")
        salary_df["salary"] = salary_df.salary.str.replace("$", "").str.replace(",", "").astype(int)

        print("Saving salary data..")
        output_path = os.path.join(
            os.path.dirname(__file__), f"../data/salaries/dk_salary_{self.current_year}_w{self.current_week}.csv"
        )
        salary_df.drop_duplicates().to_csv(output_path, index=False)

    def time_until_run(self, now: datetime):
        # Check if today is Tuesday and if we are past 12:00 PM
        if now.weekday() == 1 and now.hour >= 12:
            # Schedule for the next Tuesday
            days_until_tuesday = 7
        else:
            # Schedule for the upcoming Tuesday (which could be today if it's before noon)
            days_until_tuesday = (1 - now.weekday() + 7) % 7  # 1 represents Tuesday
        
        # Calculate next run datetime
        next_run = now + timedelta(days=days_until_tuesday)
        next_run = next_run.replace(hour=12, minute=0, second=0, microsecond=0)
        return (next_run - now).total_seconds()

    def run(self):
        # Run scraper on-demand
        if self.on_demand:
            self.scrape()
        # Run scraper once a week, every Tuesday at 12:00 PM EST
        else:
            print("Starting weekly schedule mode. Will scrape every Tuesday at 12:00 PM EST.")
            while True:
                est = pytz.timezone("America/New_York")
                now = datetime.now(est)
                # If today is Tuesday and it's around noon (give or take 1 min)
                if (now.weekday() == 1) and (11 <= now.hour <= 12) and (abs(now.minute) <= 1):
                    self.scrape()
                    # Avoid re-running within the same window
                    sleep(180)
                else:
                    # Calculate time to sleep until next Tuesday noon
                    now = datetime.now(est)
                    time_until_next_run = self.time_until_run(now)
                    print(f"Sleeping {time_until_next_run // 60} min until next run")
                    sleep(time_until_next_run)


if __name__ == "__main__":
    scraper = SalaryScraper(on_demand=True)
    scraper.run()
