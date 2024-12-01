from datetime import datetime
from typing import List, Optional

import pandas as pd
import pulp
from app.configs.configs import NFLTeam, log
from app.helpers.optimize import get_current_week, get_stats, get_weekly_rankings
from pulp import PULP_CBC_CMD


class DFSLineupOptimizer:
    def __init__(self, year: Optional[int] = None, week: Optional[int] = None):
        self.current_year = datetime.now().year if year is None else year
        self.current_week = get_current_week(year=self.current_year) if week is None else week

    def get_salary_df(self) -> pd.DataFrame:
        path_to_csv = f"/app/data/salaries/dk_salary_{self.current_year}_w{self.current_week}.csv"
        return pd.read_csv(path_to_csv)

    def get_projections_df(self, use_stored_data: bool = False) -> pd.DataFrame:
        year = self.current_year
        week = self.current_week

        if use_stored_data:
            log.info("Using stored data")
            return pd.read_csv(f"/app/data/projections/fp_projection_{year}_w{week}.csv")
        
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
        df = df.merge(self.get_salary_df())
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
        df = df.fillna(0)
        output_path = f"/app/data/projections/fp_projection_{year}_w{week}.csv"
        df.drop_duplicates().to_csv(output_path, index=False)
        return df

    def get_lineup_df(
        self,
        dst: Optional[NFLTeam] = None,
        one_te: Optional[bool] = False,
        use_avg_fpts: bool = False,
        weights: dict = {},
        exclude_players: List[str] = [],
        include_players: List[str] = [],
        use_stored_data: bool = False,
    ) -> pd.DataFrame:
        selected_players = []
        budget = 50000
        total_players = 9
        QB_limit, RB_limit, WR_limit, TE_limit, DST_limit = 1, 2, 3, 1, 1

        # Get data
        df = self.get_projections_df(use_stored_data=use_stored_data)

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
                        log.warning("Warning: Already selected max number of QBs")
                    else:
                        QB_limit -= 1
                elif player_row["position"].values[0] == "RB":
                    if RB_limit == 0:
                        log.warning("Warning: Already selected max number of RBs")
                    else:
                        RB_limit -= 1
                elif player_row["position"].values[0] == "WR":
                    if WR_limit == 0:
                        log.warning("Warning: Already selected max number of WRs")
                    WR_limit -= 1
                elif player_row["position"].values[0] == "TE":
                    if TE_limit == 0:
                        log.warning("Warning: Already selected max number of TEs")
                    else:
                        TE_limit -= 1
                else:
                    if DST_limit == 0:
                        log.warning("Warning: Already selected max number of DSTs")
                    else:
                        DST_limit -= 1
            else:
                log.warning(f"Warning: Player '{player}' not found in the dataset.")

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
