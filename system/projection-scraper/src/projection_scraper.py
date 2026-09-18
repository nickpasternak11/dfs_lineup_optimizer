from datetime import datetime

import pandas as pd
from src.configs import log
from src.utils import (
    get_current_player_injuries,
    get_current_week,
    get_stats,
    get_weekly_rankings,
)


class ProjectionScraper:
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

    def get_salary_df(
        self, year: int | None = None, week: int | None = None
    ) -> pd.DataFrame:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        path_to_csv = f"/app/data/salaries/dk_salary_{year}_w{week}.csv"
        return pd.read_csv(path_to_csv)

    def scrape(self, year: int | None = None, week: int | None = None) -> None:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week

        log.info(
            "Scraping projections from FantasyPro's for year=%s, week=%s", year, week
        )

        # Get weekly rankings and stats for all positions
        df = pd.DataFrame()
        for pos in ["QB", "RB", "WR", "TE", "DST"]:
            df = pd.concat(
                [
                    df,
                    pd.merge(
                        get_weekly_rankings(pos, self.fp_year, week),
                        get_stats(pos, self.fp_year, [week - 4, week - 1])[
                            ["player", "avg_fpts"]
                        ],
                        how="left",
                    ),
                ]
            )

        # Merge with salary data and calculate value
        df = df.merge(self.get_salary_df(year=year, week=week))
        df = df[
            [
                "year",
                "week",
                "player",
                "position",
                "team",
                "kickoff",
                "opponent",
                "home",
                "grade",
                "rank",
                "avg_fpts",
                "proj_fpts",
                "salary",
                "salary_change",
            ]
        ]
        df["value"] = df["proj_fpts"] / (df["salary"] / 1000)

        # Integrate player injury data
        injuries_df = get_current_player_injuries().fillna("Healthy")
        df = pd.merge(
            df,
            injuries_df[["player", "injury_status", "injury_type"]],
            how="left",
            on="player",
        )

        log.info("Saving projection data..")
        output_path = f"/app/data/projections/fp_projection_{year}_w{week}.csv"
        df.fillna(0).drop_duplicates().to_csv(output_path, index=False)


if __name__ == "__main__":
    scraper = ProjectionScraper()
    for year in range(2018, scraper.current_year + 1):
        log.info(f"Scraping projection data for year {year}..")
        scraper.scrape(year=year)
