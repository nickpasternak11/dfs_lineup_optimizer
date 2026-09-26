from datetime import datetime

import pandas as pd
from dfs_db import PlayerProjection, replace_weeks, session_scope
from dfs_db.upsert import DEFAULT_MIN_RATIO
from src.configs import log
from src.utils import (
    get_current_week,
    get_player_injuries,
    get_stats,
    get_weekly_rankings,
)

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]


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

    def scrape(
        self,
        year: int | None = None,
        week: int | None = None,
        allow_shrink: bool = False,
    ) -> None:
        year = self.fp_year if year is None else year
        week = self.current_week if week is None else week

        log.info(
            "Scraping projections from FantasyPro's for year=%s, week=%s", year, week
        )

        # Get weekly rankings and stats for all positions
        df = pd.DataFrame()
        for pos in POSITIONS:
            rankings = get_weekly_rankings(pos, year, week)
            # One empty position would still leave a plausible-looking week,
            # and saving it would replace a complete one.
            if rankings.empty:
                raise RuntimeError(f"No {pos} rankings for year={year}, week={week}")
            df = pd.concat(
                [
                    df,
                    pd.merge(
                        rankings,
                        get_stats(pos, year, [week - 4, week - 1])[
                            ["player", "avg_fpts"]
                        ],
                        how="left",
                    ),
                ]
            )

        # Integrate the week's injury report. Players absent from it are left
        # NULL rather than filled, so "no report" stays distinguishable from a
        # real status.
        injuries_df = get_player_injuries(year, week)
        df = pd.merge(
            df,
            injuries_df[["player", "injury_status", "injury_type"]],
            how="left",
            on="player",
        )

        # Salary, team, opponent, kickoff and home live on player_salaries and
        # are joined back in by the weekly_player_pool view.
        df = df.assign(year=year, week=week)

        log.info("Saving projection data..")
        with session_scope() as session:
            rows = replace_weeks(
                session,
                PlayerProjection,
                df,
                min_ratio=0 if allow_shrink else DEFAULT_MIN_RATIO,
            )
        log.info("Upserted %s projection rows for year=%s, week=%s", rows, year, week)


if __name__ == "__main__":
    ProjectionScraper().scrape()
