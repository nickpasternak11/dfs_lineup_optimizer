import os
from datetime import datetime
from typing import Optional

import pandas as pd

from utils import get_current_week, get_stats, get_weekly_rankings
from configs import log


class ProjectionScraper:
    def __init__(self):
        self.current_year = datetime.now().year
        self.current_week = get_current_week(year=self.current_year)

    def get_salary_df(self, year: Optional[int] = None, week: Optional[int] = None) -> pd.DataFrame:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        path_to_csv = os.path.join(
            os.path.dirname(__file__), f"../data/salaries/dk_salary_{year}_w{week}.csv"
        )
        # path_to_csv = f"/app/data/salaries/dk_salary_{year}_w{week}.csv"
        return pd.read_csv(path_to_csv)

    def scrape(self, year: Optional[int] = None, week: Optional[int] = None) -> None:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        df = pd.DataFrame()

        log.info("Scraping projections from FantasyPro's for year=%s, week=%s", year, week)

        for pos in ["QB", "RB", "WR", "TE", "DST"]:
            df = pd.concat(
                [
                    df,
                    pd.merge(
                        get_weekly_rankings(pos, year, week),
                        get_stats(pos, year, [week - 4, week - 1])[["player", "avg_fpts"]],
                        how="left",
                    ),
                ]
            )

        df["player"] = df.apply(
            lambda x: (
                x["player"].split()[-1]
                if x["position"] == "DST"
                else x["player"]
                .replace("II", "")
                .replace(" I", "")
                .replace("Jr.", "")
                .replace("Sr.", "")
                .replace(".", "")
                .replace("'", "")
                .strip()
            ),
            axis=1,
        )
        df = df[~df.grade.isin(["F", "D-", "D", "D+"])]
        df = df.merge(self.get_salary_df(year=year, week=week))
        df = df[
            [
                "year",
                "week",
                "player",
                "position",
                "team",
                "opponent",
                "grade",
                "rank",
                "avg_fpts",
                "proj_fpts",
                "salary",
            ]
        ]

        log.info("Saving projection data..")
        output_path = os.path.join(
            os.path.dirname(__file__), f"../data/projections/fp_projection_{self.current_year}_w{self.current_week}.csv"
        )
        df.fillna(0).drop_duplicates().to_csv(output_path, index=False)


if __name__ == "__main__":
    log.info("Starting projection scraper..")
    scraper = ProjectionScraper()
    scraper.scrape()
