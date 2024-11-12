import json
import os
from datetime import datetime
from typing import List, Optional

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
        # hack
        # df = df[~df.team.isin(["MIN", "LAR"])]
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
        exclude_players: List[str] = [],
        include_players: List[str] = [],
    ) -> pd.DataFrame:
        selected_players = []
        budget = 50000
        total_players = 9
        QB_limit, RB_limit, WR_limit, TE_limit, DST_limit = 1, 2, 3, 1, 1

        # Get data
        year = self.current_year if year is None else year
        week = self.current_week if week is None else week
        df = self.get_fantasypros_df(year=year, week=week)

        # If specified, factor in avg_fpts
        if use_avg_fpts:
            df["proj_fpts"] = round(df["proj_fpts"] * weights["proj_fpts"] + df["avg_fpts"] * weights["avg_fpts"], 1)

        # Handle excluded players
        df = df[~df["player"].isin(exclude_players)]

        # Handle selected DST
        if dst:
            defense_row = df[(df["position"] == "DST") & (df["player"].str.contains(dst, case=False))]
            if not defense_row.empty:
                dst_player = defense_row["player"].values[0]
                if (dst_player not in exclude_players) and (dst_player not in include_players):
                    selected_players.append(dst_player)
                    budget -= defense_row["salary"].values[0]
                    total_players -= 1
                    DST_limit = 0
            else:
                raise ValueError(f"Defense '{dst}' not found.")

        # Handle included players
        for player in include_players:
            player_row = df[df["player"] == player]
            if not player_row.empty:
                selected_players.append(player)
                budget -= player_row["salary"].values[0]
                total_players -= 1
                if player_row["position"].values[0] == "QB":
                    if QB_limit == 0:
                        print("Warning: Already selected max number of QBs")
                    else:
                        QB_limit -= 1
                elif player_row["position"].values[0] == "RB":
                    if RB_limit == 0:
                        print("Warning: Already selected max number of RBs")
                    else:
                        RB_limit -= 1
                elif player_row["position"].values[0] == "WR":
                    if WR_limit == 0:
                        print("Warning: Already selected max number of WRs")
                    WR_limit -= 1
                elif player_row["position"].values[0] == "TE":
                    if TE_limit == 0:
                        print("Warning: Already selected max number of TEs")
                    else:
                        TE_limit -= 1
                else:
                    if DST_limit == 0:
                        print("Warning: Already selected max number of DSTs")
                    else:
                        DST_limit -= 1
            else:
                print(f"Warning: Player '{player}' not found in the dataset.")

        # Remove selected players from the dataframe used for sampling
        opt_df = df[~df["player"].isin(selected_players)]

        # Create the optimization problem
        prob = pulp.LpProblem("FantasyFootballOptimization", pulp.LpMaximize)

        # Decision variables
        selected_vars = pulp.LpVariable.dicts("Selected", opt_df.index, cat="Binary")

        # Objective function
        prob += pulp.lpSum(opt_df.loc[i, "proj_fpts"] * selected_vars[i] for i in opt_df.index)

        # Constraints
        prob += pulp.lpSum(selected_vars[i] for i in opt_df.index) == total_players
        prob += pulp.lpSum(opt_df.loc[i, "salary"] * selected_vars[i] for i in opt_df.index) <= budget
        prob += pulp.lpSum(selected_vars[i] for i in opt_df.index if opt_df.loc[i, "position"] == "QB") == QB_limit
        prob += pulp.lpSum(selected_vars[i] for i in opt_df.index if opt_df.loc[i, "position"] == "RB") >= RB_limit
        prob += pulp.lpSum(selected_vars[i] for i in opt_df.index if opt_df.loc[i, "position"] == "WR") >= WR_limit
        if one_te:
            prob += pulp.lpSum(selected_vars[i] for i in opt_df.index if opt_df.loc[i, "position"] == "TE") == TE_limit
        else:
            prob += pulp.lpSum(selected_vars[i] for i in opt_df.index if opt_df.loc[i, "position"] == "TE") >= TE_limit
        prob += pulp.lpSum(selected_vars[i] for i in opt_df.index if opt_df.loc[i, "position"] == "DST") == DST_limit

        # Solve the problem
        solver = PULP_CBC_CMD(msg=False)
        prob.solve(solver)

        # Return the selected players
        selected_players.extend([opt_df.loc[i, "player"] for i in opt_df.index if selected_vars[i].varValue == 1])
        selected_lineup = df[df["player"].isin(selected_players)]
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
