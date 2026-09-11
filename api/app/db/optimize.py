from datetime import datetime

import pandas as pd
import pulp
from pulp import PULP_CBC_CMD

from app.configs.configs import log
from app.helpers.optimize import get_latest_week, get_stats, get_weekly_rankings


class DFSLineupOptimizer:
    def __init__(self, year: int | None = None, week: int | None = None):
        self.current_year = datetime.now().year if year is None else year
        self.current_week = get_latest_week(year=year) if week is None else week

    def get_salary_df(self) -> pd.DataFrame:
        path_to_csv = (
            f"/app/data/salaries/dk_salary_{self.current_year}_w{self.current_week}.csv"
        )
        return pd.read_csv(path_to_csv)

    def get_projections_df(self, use_stored_data: bool = False) -> pd.DataFrame:
        year = self.current_year
        week = self.current_week

        if use_stored_data:
            log.info("Using stored data")
            return pd.read_csv(
                f"/app/data/projections/fp_projection_{year}_w{week}.csv"
            )

        df = pd.DataFrame()
        for pos in ["QB", "RB", "WR", "TE", "DST"]:
            df = pd.concat(
                [
                    df,
                    pd.merge(
                        get_weekly_rankings(pos, year, week),
                        get_stats(pos, year, [week - 4, week - 1])[
                            ["player", "avg_fpts"]
                        ],
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
        df["value"] = df["proj_fpts"] / (df["salary"] / 1000)

        log.info("Saving projection data..")
        df = df.fillna(0)
        output_path = f"/app/data/projections/fp_projection_{year}_w{week}.csv"
        df.drop_duplicates().to_csv(output_path, index=False)
        return df

    def optimize(
        self,
        use_avg_fpts: bool = False,
        weights: dict = {},
        stack_qb: bool = False,
        excluded_players: list[str] = [],
        included_players: list[str] = [],
        use_stored_data: bool = False,
    ) -> pd.DataFrame:
        # selected_players = []
        budget = 50000
        total_players = 9
        QB_limit, RB_limit, WR_limit, TE_limit, DST_limit, FLEX_limit = 1, 2, 3, 1, 1, 1

        # Get data
        df = self.get_projections_df(use_stored_data=use_stored_data).copy()

        # Remove excluded players
        df = df[~df["player"].isin(excluded_players)].reset_index(drop=True)

        # Validate included players exist in dataset
        missing_includes = set(included_players) - set(df["player"])
        if missing_includes:
            raise ValueError(
                f"Error: Included players not found in dataset: {missing_includes}"
            )

        # Factor in avg_fpts if requested
        if use_avg_fpts and weights:
            df["proj_fpts"] = (
                df["proj_fpts"] * weights.get("proj_fpts", 1.0)
                + df["avg_fpts"] * weights.get("avg_fpts", 0.0)
            ).round(1)

        # # Handle included players
        # for player in included_players:
        #     player_row = df[df["player"] == player]
        #     if player_row.empty:
        #         raise ValueError(f"Error: Player '{player}' not found in the dataset.")

        #     error_message = None
        #     player_position = player_row["position"].values[0]
        #     player_salary = player_row["salary"].values[0]

        #     if player_position == "QB":
        #         if QB_limit == 0:
        #             error_message = "Error: Already selected max number of QBs"
        #         else:
        #             QB_limit -= 1
        #     elif player_position == "RB":
        #         if (RB_limit + FLEX_limit) == 0:
        #             error_message = "Error: Already selected max number of RBs"
        #         else:
        #             RB_limit -= 1
        #     elif player_position == "WR":
        #         if (WR_limit + FLEX_limit) == 0:
        #             error_message = "Error: Already selected max number of WRs"
        #         else:
        #             WR_limit -= 1
        #     elif player_position == "TE":
        #         if (TE_limit + FLEX_limit) == 0:
        #             error_message = "Error: Already selected max number of TEs"
        #         else:
        #             TE_limit -= 1
        #     elif player_position == "DST":
        #         if DST_limit == 0:
        #             error_message = "Error: Already selected max number of DSTs"
        #         else:
        #             DST_limit -= 1
        #     else:
        #         error_message = f"Error: Invalid position for player '{player}'"

        #     if error_message:
        #         raise ValueError(
        #             f"{error_message}. Cannot include player '{player}' in the lineup."
        #         )

        #     selected_players.append(player)
        #     budget -= player_salary
        #     total_players -= 1

        # # Remove included players from df as they are already included
        # df = df[~df["player"].isin(selected_players)]

        # # If specified, factor in avg_fpts
        # if use_avg_fpts:
        #     df["proj_fpts"] = round(
        #         df["proj_fpts"] * weights["proj_fpts"]
        #         + df["avg_fpts"] * weights["avg_fpts"],
        #         1,
        #     )

        # Create the optimization problem
        prob = pulp.LpProblem("DFS_Lineup_Optimization", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("Players", df.index, cat="Binary")

        # Objective function
        prob += pulp.lpSum(df.loc[i, "proj_fpts"] * player_vars[i] for i in df.index)

        # Total roster constraint (9 players)
        prob += pulp.lpSum(player_vars[i] for i in df.index) == total_players

        # Position constraints
        # Total 9 players: 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX (RB/WR/TE), 1 DST
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "QB"
            )
            == QB_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "RB"
            )
            >= RB_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "RB"
            )
            <= RB_limit + FLEX_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "WR"
            )
            >= WR_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "WR"
            )
            <= WR_limit + FLEX_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "TE"
            )
            >= TE_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "TE"
            )
            <= TE_limit + FLEX_limit
        )
        prob += (
            pulp.lpSum(
                player_vars[i] for i in df.index if df.loc[i, "position"] == "DST"
            )
            == DST_limit
        )

        # Salary cap constraint
        prob += (
            pulp.lpSum(df.loc[i, "salary"] * player_vars[i] for i in df.index) <= budget
        )

        # Enforce included players to be in the lineup
        player_indices = df[df["player"].isin(included_players)].index
        for idx in player_indices:
            prob += player_vars[idx] == 1

        # QB WR/TE stracking constraints
        if stack_qb:
            teams = df["team"].unique()
            for team in teams:
                qb_vars = [
                    player_vars[i]
                    for i in df.index
                    if df.loc[i, "team"] == team and df.loc[i, "position"] == "QB"
                ]
                pass_catcher_vars = [
                    player_vars[i]
                    for i in df.index
                    if df.loc[i, "team"] == team
                    and df.loc[i, "position"] in ["WR", "TE"]
                ]

                if qb_vars:
                    prob += (
                        pulp.lpSum(pass_catcher_vars) >= pulp.lpSum(qb_vars),
                        f"QB_Stack_{team}",
                    )

        # Solve the problem
        solver = PULP_CBC_CMD(msg=False)
        prob.solve(solver)

        if pulp.LpStatus[prob.status] != "Optimal":
            raise ValueError(
                "No optimal lineup could be found with the current constraints."
            )

        # Return selected players
        selected_indices = [i for i in df.index if player_vars[i].varValue == 1]
        return df.loc[selected_indices]

    def get_optimal_lineups(
        self,
        stack_qb: bool = False,
        excluded_players: list[str] = [],
        included_players: list[str] = [],
        use_stored_data: bool = True,
    ) -> list[dict]:
        lineups = []
        for weights in [(1, 0), (0.9, 0.1), (0.8, 0.2)]:
            log.info("weights=%s", weights)
            lineup = self.optimize(
                use_avg_fpts=True if weights[1] > 0 else False,
                weights={"proj_fpts": weights[0], "avg_fpts": weights[1]},
                stack_qb=stack_qb,
                excluded_players=excluded_players,
                included_players=included_players,
                use_stored_data=use_stored_data,
            )
            lineups.append(lineup.to_dict(orient="records"))
        return lineups
