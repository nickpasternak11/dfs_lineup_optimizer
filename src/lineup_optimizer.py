import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import pulp
from pulp import PULP_CBC_CMD
from tabulate import tabulate

from configs import NFLTeam
from utils import get_current_week, get_stats, get_weekly_rankings


class DFSLineupOptimizer:
    def __init__(self):
        self.current_year = datetime.now().year
        self.current_week = get_current_week(year=self.current_year)

    def get_salary_df(self, year: Optional[int] = None, week: Optional[int] = None) -> pd.DataFrame:
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        path_to_csv = f"/app/data/salaries/dk_salary_{year}_w{week}.csv"
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
        df = df[["year", "week", "player", "position", "team", "opponent", "rank", "avg_fpts", "proj_fpts", "salary"]]
        return df.fillna(0)

    def save_lineup(self, selected_lineup: pd.DataFrame, year: int, week: int, params: dict) -> None:
        # Convert the lineup DataFrame to a dictionary
        lineup_dict = selected_lineup.to_dict(orient="records")

        # Create the filename
        filename = f"/app/data/lineups/dk_lineup_{year}_w{week}.json"

        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Check if the file exists
        if os.path.exists(filename):
            # If it exists, read the existing data
            with open(filename, "r") as f:
                existing_data = json.load(f)

            # Append the new lineup
            existing_data.append({"timestamp": datetime.now().isoformat(), "lineup": lineup_dict, "params": params})

            # Write the updated data back to the file
            with open(filename, "w") as f:
                json.dump(existing_data, f, indent=2)
        else:
            # If the file doesn't exist, create it with the new lineup
            with open(filename, "w") as f:
                json.dump(
                    [{"timestamp": datetime.now().isoformat(), "lineup": lineup_dict, "params": params}], f, indent=2
                )

    def get_lineup_df(
        self,
        year: Optional[int] = None,
        week: Optional[int] = None,
        dst: Optional[NFLTeam] = None,
        one_te: Optional[bool] = False,
        use_avg_fpts: bool = False,
        weights: dict = {},
    ) -> pd.DataFrame:
        selected_players = []
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        df = self.get_fantasypros_df(year=year, week=week)

        if dst:
            defense_row = df[(df["position"] == "DST") & (df["player"].str.contains(dst, case=False))]
            if not defense_row.empty:
                def_salary = defense_row["salary"].values[0]
                selected_players.append(dst)
            else:
                raise ValueError(f"Defense '{dst}' not found.")
        else:
            def_salary = 0

        if use_avg_fpts:
            df["proj_fpts"] = round(df["proj_fpts"] * weights["proj_fpts"] + df["avg_fpts"] * weights["avg_fpts"], 1)

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
        if one_te:
            prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "TE") == TE_limit
        else:
            prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "TE") >= TE_limit
        prob += pulp.lpSum(selected_vars[i] for i in df.index if df.loc[i, "position"] == "DST") == DST_limit

        # Solve the problem
        solver = PULP_CBC_CMD(msg=False)
        prob.solve(solver)

        # Return the selected players
        selected_players.extend([df.loc[i, "player"] for i in df.index if selected_vars[i].varValue == 1])
        selected_lineup = df[df["player"].isin(selected_players)]

        # save lineup
        self.save_lineup(
            selected_lineup=selected_lineup,
            year=year,
            week=week,
            params={
                "dst": dst,
                "one_te": one_te,
                "use_avg_fpts": use_avg_fpts,
                "weights": weights,
            },
        )

        return selected_lineup


if __name__ == "__main__":
    optimizer = DFSLineupOptimizer()
    week = int(os.getenv("WEEK", None)) if os.getenv("WEEK", None) else None
    one_te = os.getenv("ONE_TE", False)
    dst = os.getenv("DST", None)

    lineup = optimizer.get_lineup_df(week=week, dst=dst, one_te=one_te)
    print("\nSelected Players:")
    print(tabulate(lineup, headers="keys", tablefmt="pretty", showindex=False))
    print(f"Projected FantasyPros FPTS: {lineup.proj_fpts.sum()}")

    lineup = optimizer.get_lineup_df(
        week=week, dst=dst, one_te=one_te, use_avg_fpts=True, weights={"proj_fpts": 0.90, "avg_fpts": 0.10}
    )
    print("\nSelected Players:")
    print(tabulate(lineup, headers="keys", tablefmt="pretty", showindex=False))
    print(f"Projected FantasyPros FPTS: {lineup.proj_fpts.sum()}")

    lineup = optimizer.get_lineup_df(
        week=week, dst=dst, one_te=one_te, use_avg_fpts=True, weights={"proj_fpts": 0.80, "avg_fpts": 0.20}
    )
    print("\nSelected Players:")
    print(tabulate(lineup, headers="keys", tablefmt="pretty", showindex=False))
    print(f"Projected FantasyPros FPTS: {lineup.proj_fpts.sum()}")
