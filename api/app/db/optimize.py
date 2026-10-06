import pandas as pd
import pulp
from dfs_common.season import current_season_year
from dfs_db import get_engine
from pulp import PULP_CBC_CMD
from sqlalchemy import text

from app.configs.configs import API_CACHE_TTL_SECONDS, log
from app.helpers.cache import TTLCache
from app.helpers.optimize import dataframe_to_records, get_latest_week

# The weeks FantasyPros' recent average covers, and the matchup ranks use:
# the four before the slate, or all of last regular season in week 1.
_RECENT_WEEKS = """
    season_type = 'REG'
    AND CASE WHEN :week = 1 THEN year = :year - 1
             ELSE year = :year AND week BETWEEN :week - 4 AND :week - 1 END
"""

# player_week_results adds each player's nflverse id (for their game log)
# and, once the game is final, the DraftKings points they actually scored.
#
# avg_fpts is rescored in DraftKings points from the game logs: FantasyPros'
# own average is full PPR, which has no yardage bonuses and takes 2 for a
# turnover, so it ran ~0.4 points a game below DraftKings (1.2 for QBs).
# Players we can't link to nflverse keep FantasyPros' number.
#
# The matchup columns rank the opponent by the FPTS it allowed to the
# player's position per game over the same weeks: 1 allowed the fewest (the
# toughest matchup), 32 the most. A defense's matchup is the offense it
# faces, ranked by what it gave up to the DSTs it played.
#
# The betting lines come from the nflverse schedule, refreshed with the game
# logs each morning. nflverse's spread_line is the home team's expected
# margin; team_spread flips it to the team's own, betting-style (favorites
# negative), so its implied total is (total - spread) / 2.
PLAYER_POOL_QUERY = text(
    f"""
    WITH defense_games AS (
        SELECT year, week, nfl_team(team) AS defense, nfl_team(opponent) AS offense, dk_points
        FROM dst_game_logs
        WHERE {_RECENT_WEEKS}
    ),
    allowed AS (
        -- One row per defense, position and game; a game where nobody at a
        -- position scored still counts, as zero.
        SELECT games.defense AS team, positions.position,
               COALESCE(sum(logs.dk_points), 0) AS points
        FROM defense_games AS games
        CROSS JOIN (VALUES ('QB'), ('RB'), ('WR'), ('TE')) AS positions (position)
        LEFT JOIN player_game_logs AS logs
          ON logs.year = games.year
         AND logs.week = games.week
         AND nfl_team(logs.opponent) = games.defense
         AND CASE logs.position WHEN 'FB' THEN 'RB' ELSE logs.position END = positions.position
        GROUP BY games.defense, positions.position, games.year, games.week
        UNION ALL
        SELECT offense, 'DST', dk_points
        FROM defense_games
    ),
    matchups AS (
        SELECT team, position, round(avg(points), 2) AS fpts_allowed, count(*) AS games,
               rank() OVER (PARTITION BY position ORDER BY avg(points)) AS fpts_allowed_rank
        FROM allowed
        GROUP BY team, position
    ),
    recent AS (
        SELECT gsis_id, NULL AS team, round(avg(dk_points), 2) AS dk_avg
        FROM player_game_logs
        WHERE {_RECENT_WEEKS}
        GROUP BY gsis_id
        UNION ALL
        SELECT NULL, nfl_team(team), round(avg(dk_points), 2)
        FROM dst_game_logs
        WHERE {_RECENT_WEEKS}
        GROUP BY nfl_team(team)
    )
    SELECT pool.year, pool.week, pool.player, pool.position, pool.team,
           pool.kickoff, pool.opponent, pool.home, pool.grade, pool.rank,
           COALESCE(recent.dk_avg, pool.avg_fpts) AS avg_fpts,
           pool.proj_fpts, pool.salary, pool.salary_change,
           pool.value, pool.injury_status, pool.injury_type, pool.fp_player_id,
           results.gsis_id, results.actual_dk_points,
           matchups.fpts_allowed AS opp_fpts_allowed,
           matchups.fpts_allowed_rank AS opp_fpts_allowed_rank,
           matchups.games AS opp_games,
           lines.total_line AS game_total,
           lines.spread AS team_spread,
           round((lines.total_line - lines.spread) / 2, 2) AS implied_total,
           model.proj_dk_points AS model_fpts
    FROM weekly_player_pool AS pool
    LEFT JOIN player_week_results AS results
      ON results.year = pool.year
     AND results.week = pool.week
     AND results.player = pool.player
    LEFT JOIN recent
      ON CASE WHEN pool.position = 'DST' THEN recent.team = nfl_team(pool.team)
              ELSE recent.gsis_id = results.gsis_id END
    LEFT JOIN matchups
      ON matchups.team = nfl_team(pool.opponent)
     AND matchups.position = pool.position
    LEFT JOIN LATERAL (
        SELECT games.total_line,
               CASE WHEN games.home_team = nfl_team(pool.team)
                    THEN -games.spread_line ELSE games.spread_line END AS spread
        FROM nfl_games AS games
        WHERE games.year = pool.year
          AND games.week = pool.week
          AND nfl_team(pool.team) IN (games.home_team, games.away_team)
    ) AS lines ON true
    -- Our model's latest projection made before the player's kickoff.
    LEFT JOIN LATERAL (
        SELECT snapshot.proj_dk_points
        FROM model_projections AS snapshot
        WHERE snapshot.year = pool.year
          AND snapshot.week = pool.week
          AND snapshot.player = pool.player
          AND (pool.kickoff IS NULL OR snapshot.generated_at < pool.kickoff)
        ORDER BY snapshot.generated_at DESC
        LIMIT 1
    ) AS model ON true
    WHERE pool.year = :year
      AND pool.week = :week
      AND pool.salary IS NOT NULL
      AND pool.proj_fpts IS NOT NULL
    ORDER BY pool.position, pool.rank
    """
)

# NUMERIC comes back as Decimal, which pulp can't handle.
FLOAT_COLUMNS = [
    "avg_fpts", "proj_fpts", "value", "actual_dk_points", "opp_fpts_allowed",
    "game_total", "team_spread", "implied_total", "model_fpts",
]

# What the optimizer maximizes: FantasyPros' projection (proj_fpts), or our
# model's (model_fpts), which takes its place in the lineup's records.
PROJECTION_SOURCES = ("fantasypros", "model")

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

    @classmethod
    def from_frame(cls, df: pd.DataFrame, year: int, week: int) -> "DFSLineupOptimizer":
        """An optimizer over a prepared pool instead of the week's cached one
        (the hindsight-best lineup, solved on actual points)."""
        optimizer = cls(year=year, week=week)
        optimizer._projections_df = df
        return optimizer

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
        projection_source: str = "fantasypros",
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

        if projection_source == "model":
            df = df[df["model_fpts"].notna()].reset_index(drop=True)
            if df.empty:
                raise ValueError(
                    f"Our model hasn't projected year={self.current_year}, "
                    f"week={self.current_week}"
                )
            df["proj_fpts"] = df["model_fpts"]
            df["value"] = (df["proj_fpts"] / (df["salary"] / 1000)).round(2)

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
        projection_source: str = "fantasypros",
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
                projection_source=projection_source,
            )
            lineups.append(dataframe_to_records(lineup))
        return lineups
