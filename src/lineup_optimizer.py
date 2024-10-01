import os
from datetime import datetime

import pandas as pd
import pulp
from utils import get_current_week, get_stats, get_weekly_rankings


def get_df():
    current_year = datetime.now().year
    current_week = get_current_week(year=current_year)

    # get salary data
    path = os.path.join(os.path.dirname(__file__), f"../data/dk_salary_{current_year}_w{current_week}.csv")
    salary_df = pd.read_csv(path)

    # get FantasyPros data
    fp_df = pd.DataFrame()
    for pos in ["QB", "RB", "WR", "TE", "DST"]:
        fp_df = pd.concat(
            [
                fp_df,
                pd.merge(
                    get_weekly_rankings(pos, current_year, current_week),
                    get_stats(pos, 2024, [1, current_week - 1])[["player", "avg_fpts"]],
                    how="left",
                ),
            ]
        )

    fp_df["player"] = fp_df.apply(
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
    fp_df = fp_df.merge(salary_df)
    fp_df[(fp_df.salary.isna()) & (fp_df.grade != "F")]
    return fp_df


def get_lineup(df: pd.DataFrame, def_salary: int = 0, use_avg_fpts: bool = False, weights: dict = {}):
    if use_avg_fpts:
        df["proj_fpts"] = df["proj_fpts"] * weights["proj_fpts"] + df["avg_fpts"] * weights["avg_fpts"]

    df = df[~df.grade.isin(["F", "D", "D-", "D+"])]
    df = df[["player", "position", "team", "opponent", "rank", "avg_fpts", "proj_fpts", "salary"]]

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
    prob.solve()

    # Output the selected players
    selected_players = [df.loc[i, "player"] for i in df.index if selected_vars[i].varValue == 1]
    print("Selected Players:")
    print(selected_players)
    selected_lineup = df[df["player"].isin(selected_players)]
    print(f"Projected FantasyPros FPTS: {selected_lineup.proj_fpts.sum()}")
    return selected_players


if __name__ == "__main__":
    df = get_df()
    # lineup = get_lineup(df=df, use_avg_fpts=True, weights={"proj_fpts": 0.85, "avg_fpts": 0.15})
    # lineup = get_lineup(df=df, use_avg_fpts=True, weights={"proj_fpts": 0.90, "avg_fpts": 0.10})
    lineup = get_lineup(df=df)
