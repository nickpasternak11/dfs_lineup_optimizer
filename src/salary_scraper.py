import os
from datetime import datetime
from time import sleep

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from utils import get_current_week


def main():
    url = "https://draftdime.com/nfl-projections"

    current_year = datetime.now().year
    current_week = get_current_week(year=current_year)

    op = webdriver.ChromeOptions()
    op.add_argument("headless")

    with webdriver.Chrome(options=op) as browser:
        browser.get(url)
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

    salary_df = pd.io.html.read_html(str(table))[0].iloc[1:, :6]
    salary_df.columns = ["player", "extra", "position", "team", "opponent", "salary"]
    salary_df = salary_df.drop(columns=["extra"])
    salary_df["opponent"] = salary_df.opponent.str.replace("@", "")
    salary_df["salary"] = salary_df.salary.str.replace("$", "").str.replace(",", "").astype(int)

    output_path = os.path.join(os.path.dirname(__file__), f"../data/dk_salary_{current_year}_w{current_week}.csv")
    salary_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
