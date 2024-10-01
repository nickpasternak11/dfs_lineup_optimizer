from datetime import datetime

import pandas as pd
import pulp
from pulp import PULP_CBC_CMD
from utils import get_current_week, get_stats, get_weekly_rankings
from tabulate import tabulate
from typing import Optional


class DFSLineupOptimizer:
    def __init__(self):
        self.current_year = datetime.now().year
        self.current_week = get_current_week(year=self.current_year)

    def get_salary_df(self, year: Optional[int] = None, week: Optional[int] = None) -> pd.DataFrame:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        path_to_csv = f"/app/data/dk_salary_{year}_w{week}.csv"
        return pd.read_csv(path_to_csv)

    def get_fantasypros_df(self, year: Optional[int] = None, week: Optional[int] = None) -> pd.DataFrame:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        df = pd.DataFrame()

        for pos in ["QB", "RB", "WR", "TE", "DST"]:
            df = pd.concat(
                [
                    df,
                    pd.merge(
                        get_weekly_rankings(pos, year, week),
                        get_stats(pos, 2024, [1, week - 1])[["player", "avg_fpts"]],
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
        df = df.merge(self.get_salary_df(year=year, week=week))
        df = df[~df.grade.isin(["F", "D", "D-", "D+"])]
        df = df[["player", "position", "team", "opponent", "rank", "avg_fpts", "proj_fpts", "salary"]]
        return df

    def get_lineup_df(
        self,
        year: Optional[int] = None,
        week: Optional[int] = None,
        def_salary: int = 0,
        use_avg_fpts: bool = False,
        weights: dict = {},
    ) -> pd.DataFrame:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        df = self.get_fantasypros_df(year=year, week=week)

        if use_avg_fpts:
            df["proj_fpts"] = df["proj_fpts"] * weights["proj_fpts"] + df["avg_fpts"] * weights["avg_fpts"]

        # Constants
        budget = 50000 if def_salary <= 0 else (50000 - def_salary)
        total_players = 9 if def_salary <= 0 else 8
        QB_limit = 1
        RB_limit = 2
        WR_limit = 3
        TE_limit = 1
        DST_limit = 1 if def_salary <= 0 else 0

        # Create the optimization problem
        prob = pulp.LpProblem("FantasyFootballOptimization", pulp.LpMaximize)

        # Decision variables
        selected_vars = pulp.LpVariable.dicts("Selected", df.index, cat="Binary")

        # Objective function
        prob += pulp.lpSum(df.loc[i, "proj_fpts"] * selected_vars[i] for i in df.index)

        # Constraints
        prob += pulp.lpSum(selected_vars[i] for i in df.index) == total_players
        prob += pulp.lpSum(df.loc[i, "salary"] * selected_vars[i] for i in df.index) <= budget
        prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "QB") == QB_limit
        prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "RB") >= RB_limit
        prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "WR") >= WR_limit
        prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "TE") >= TE_limit
        prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "DST") == DST_limit

        # Solve the problem
        solver = PULP_CBC_CMD(msg=False)
        prob.solve(solver)

        # Return the selected players
        selected_players = [df.loc[i, "player"] for i in df.index if selected_vars[i].varValue == 1]
        selected_lineup = df[df["player"].isin(selected_players)]
        return selected_lineup


if __name__ == "__main__":
    optimizer = DFSLineupOptimizer()

    # lineup = optimizer.get_lineup_df(use_avg_fpts=True, weights={"proj_fpts": 0.85, "avg_fpts": 0.15})
    lineup = optimizer.get_lineup_df(use_avg_fpts=True, weights={"proj_fpts": 0.90, "avg_fpts": 0.10})
    # lineup = optimizer.get_lineup_df()

    print("\nSelected Players:")
    print(tabulate(lineup, headers="keys", tablefmt="pretty", showindex=False))
    print(f"Projected FantasyPros FPTS: {lineup.proj_fpts.sum()}")
