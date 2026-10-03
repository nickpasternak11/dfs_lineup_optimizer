import pandas as pd
import pulp
from dfs_common.season import current_season_year
from dfs_db import get_engine
from pulp import PULP_CBC_CMD
from sqlalchemy import text

from app.configs.configs import API_CACHE_TTL_SECONDS, log
from app.helpers.cache import TTLCache
from app.helpers.optimize import dataframe_to_records, get_latest_week

PLAYER_POOL_QUERY = text(
    """
    SELECT year, week, player, position, team, kickoff, opponent, home,
           grade, rank, avg_fpts, proj_fpts, salary, salary_change, value,
           injury_status, injury_type
    FROM weekly_player_pool
    WHERE year = :year
      AND week = :week
      AND salary IS NOT NULL
      AND proj_fpts IS NOT NULL
    ORDER BY position, rank
    """
)

# NUMERIC comes back as Decimal, which neither pulp nor orjson can handle.
FLOAT_COLUMNS = ["avg_fpts", "proj_fpts", "value"]

# Player pools keyed by (year, week), shared by every request in this worker.
# Each caller gets its own copy, so filtering or reweighting one request's
# frame can never leak into another's.
_player_pool_cache = TTLCache(API_CACHE_TTL_SECONDS, copy=pd.DataFrame.copy)


def load_player_pool(year: int, week: int) -> pd.DataFrame:
    with get_engine().connect() as connection:
        df = pd.read_sql(
            PLAYER_POOL_QUERY, connection, params={"year": year, "week": week}
        )
    for column in FLOAT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


class DFSLineupOptimizer:
    def __init__(self, year: int | None = None, week: int | None = None):
        self.current_year = current_season_year() if year is None else year
        self.current_week = (
            get_latest_week(year=self.current_year) if week is None else week
        )
        self._projections_df: pd.DataFrame | None = None

    def get_projections_df(self) -> pd.DataFrame:
        """The week's player pool, from the process-wide cache.

        get_optimal_lineups solves three times over the same pool, so the
        instance keeps its own copy; callers copy before mutating.
        """
        if self._projections_df is None:
            year, week = self.current_year, self.current_week
            self._projections_df = _player_pool_cache.get_or_load(
                (year, week), lambda: load_player_pool(year, week)
            )
        return self._projections_df

    def optimize(
        self,
        use_avg_fpts: bool = False,
        weights: dict = {},
        stack_qb_count: int = 0,
        avoid_te_flex: bool = False,
        include_started_players: bool = False,
        excluded_players: list[str] = [],
        included_players: list[str] = [],
    ) -> pd.DataFrame:
        # selected_players = []
        budget = 50000
        total_players = 9
        QB_limit, RB_limit, WR_limit, TE_limit, DST_limit, FLEX_limit = 1, 2, 3, 1, 1, 1

        # Get data
        df = self.get_projections_df().copy()

        if df.empty:
            # Mapped to a 404 by the route, matching the old missing-CSV case.
            raise FileNotFoundError(
                f"No player pool for year={self.current_year}, "
                f"week={self.current_week}"
            )

        # By default, only players whose games have not started are eligible.
        # Slates predating kickoff collection have it NULL and stay eligible.
        if not include_started_players:
            kickoff = pd.to_datetime(df["kickoff"], errors="coerce", utc=True)
            df = df[kickoff.isna() | (kickoff > pd.Timestamp.now(tz="UTC"))]

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
            # Players with no recent stats (rookies, returns from injury) have
            # NULL avg_fpts; fall back to their projection so the blend leaves
            # them unchanged instead of going NaN.
            avg_fpts = df["avg_fpts"].fillna(df["proj_fpts"])
            df["proj_fpts"] = (
                df["proj_fpts"] * weights.get("proj_fpts", 1.0)
                + avg_fpts * weights.get("avg_fpts", 0.0)
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

        # Create the optimization problem. Columns are read into plain lists
        # once: per-cell df.loc lookups inside these loops (O(players x teams)
        # with stacking) used to cost far more than the CBC solve itself.
        prob = pulp.LpProblem("DFS_Lineup_Optimization", pulp.LpMaximize)
        player_vars = pulp.LpVariable.dicts("Players", df.index, cat="Binary")
        rows = list(
            zip(
                df.index,
                df["position"].tolist(),
                df["team"].tolist(),
                df["proj_fpts"].tolist(),
                df["salary"].tolist(),
            )
        )
        position_vars: dict[str, list] = {}
        for i, position, _, _, _ in rows:
            position_vars.setdefault(position, []).append(player_vars[i])

        def at_position(position: str) -> pulp.LpAffineExpression:
            return pulp.lpSum(position_vars.get(position, []))

        # Objective function
        prob += pulp.LpAffineExpression(
            (player_vars[i], proj_fpts) for i, _, _, proj_fpts, _ in rows
        )

        # Total roster constraint (9 players)
        prob += pulp.lpSum(player_vars.values()) == total_players

        # Position constraints
        # Total 9 players: 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX (RB/WR/TE), 1 DST
        prob += at_position("QB") == QB_limit
        prob += at_position("RB") >= RB_limit
        prob += at_position("RB") <= RB_limit + FLEX_limit
        prob += at_position("WR") >= WR_limit
        prob += at_position("WR") <= WR_limit + FLEX_limit
        prob += at_position("TE") >= TE_limit
        te_maximum = TE_limit if avoid_te_flex else TE_limit + FLEX_limit
        prob += at_position("TE") <= te_maximum
        prob += at_position("DST") == DST_limit

        # Salary cap constraint
        prob += (
            pulp.LpAffineExpression(
                (player_vars[i], salary) for i, _, _, _, salary in rows
            )
            <= budget
        )

        # Enforce included players to be in the lineup
        player_indices = df[df["player"].isin(included_players)].index
        for idx in player_indices:
            prob += player_vars[idx] == 1

        # QB WR/TE stracking constraints
        if stack_qb_count:
            qb_vars: dict[str, list] = {}
            pass_catcher_vars: dict[str, list] = {}
            for i, position, team, _, _ in rows:
                if position == "QB":
                    qb_vars.setdefault(team, []).append(player_vars[i])
                elif position in ["WR", "TE"]:
                    pass_catcher_vars.setdefault(team, []).append(player_vars[i])

            for team in df["team"].unique():
                # A NULL team never matched a QB before either.
                if pd.notna(team) and qb_vars.get(team):
                    prob += (
                        pulp.lpSum(pass_catcher_vars.get(team, []))
                        >= stack_qb_count * pulp.lpSum(qb_vars[team]),
                        f"QB_Stack_{team}_{stack_qb_count}",
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
        stack_qb_count: int = 0,
        avoid_te_flex: bool = False,
        include_started_players: bool = False,
        excluded_players: list[str] = [],
        included_players: list[str] = [],
    ) -> list[dict]:
        lineups = []
        for weights in [(1, 0), (0.9, 0.1), (0.8, 0.2)]:
            log.info("weights=%s", weights)
            lineup = self.optimize(
                use_avg_fpts=True if weights[1] > 0 else False,
                weights={"proj_fpts": weights[0], "avg_fpts": weights[1]},
                stack_qb_count=stack_qb_count,
                avoid_te_flex=avoid_te_flex,
                include_started_players=include_started_players,
                excluded_players=excluded_players,
                included_players=included_players,
            )
            lineups.append(dataframe_to_records(lineup))
        return lineups
