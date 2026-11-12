"""Which projection builds the best single lineup, and what do the best
lineups in hindsight look like? (#51)

Walk-forward: each season's model predictions come from a model trained only
on earlier seasons, with the live rules (ruled-out players and backup QBs at
0; before 2026's depth charts, a team's starter is its available QB with the
most recent pass attempts).

For every week with DraftKings salaries and every game final:
1. One lineup per projection (FantasyPros, our model, their average, and
   each blended 90/10 and 80/20 with the recent average), built under the
   saved lineups' rules (QB stacked with a WR/TE, no DST facing the lineup's
   players, one TE), plus FantasyPros and the model without rules. Scored
   on actual points against FantasyPros'.
2. The best lineup in hindsight, with no rules: how often it stacks, brings
   back an opposing player, plays two TEs or a DST against its own players,
   and what the rules would have cost it.

Every lineup picks only from players who played (the walk-forward has no
prediction for the rest), which lifts every score alike. Reads the
database, writes nothing; about a minute. Results from 2026-11-11 (72 weeks,
2018-2026): FantasyPros 140.4, the average 138.4 (-2.0 +/- 6.2), our model
137.1 (-3.3 +/- 8.2), and every blend below its plain projection (FP 80/20
-10.2 +/- 6.9). The hindsight best stacks its QB 51% of the time unforced;
the rules cost it 3.0 points a week.

    make experiment NAME=lineup_backtest
"""

import time
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from src import data, nflverse
from src import features as F
from src.model import walk_forward

warnings.simplefilter("ignore")

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]
SALARY_CAP = 50000
ROSTER = {"QB": (1, 1), "RB": (2, 3), "WR": (3, 4), "TE": (1, 2), "DST": (1, 1)}
START = time.time()


def say(*parts):
    print(f"[{time.time() - START:5.0f}s]", *parts, flush=True)


def solve(pool: pd.DataFrame, points: np.ndarray, rules: bool = False) -> np.ndarray | None:
    """The DraftKings classic lineup (row positions) with the most `points`;
    with `rules`, the saved lineups' rules: its QB with at least one of his
    own WRs/TEs, no DST facing its players, and one TE."""
    position, team, opponent = pool.position.to_numpy(), pool.team.to_numpy(), pool.opponent.to_numpy()
    rows, low, high = [np.ones(len(pool)), pool.salary.to_numpy(float)], [9, 0], [9, SALARY_CAP]
    roster = {**ROSTER, "TE": (1, 1)} if rules else ROSTER
    for name, (a, b) in roster.items():
        rows.append((position == name).astype(float))
        low.append(a)
        high.append(b)
    if rules:
        for qb in np.flatnonzero(position == "QB"):
            coefficients = ((team == team[qb]) & np.isin(position, ["WR", "TE"])).astype(float)
            coefficients[qb] = -1
            rows.append(coefficients)
            low.append(0)
            high.append(np.inf)
        for dst in np.flatnonzero(position == "DST"):
            coefficients = ((team == opponent[dst]) & (position != "DST")).astype(float)
            coefficients[dst] = 8
            rows.append(coefficients)
            low.append(-np.inf)
            high.append(8)
    result = milp(
        -np.asarray(points, float), constraints=LinearConstraint(np.array(rows), low, high),
        integrality=np.ones(len(pool)), bounds=Bounds(0, 1), options={"time_limit": 30},
    )
    return None if result.x is None else np.flatnonzero(result.x > 0.5)


def describe(pool: pd.DataFrame, lineup: np.ndarray) -> dict:
    """How a lineup is built: its QB stack, bring-back, TEs and DST."""
    players = pool.iloc[lineup]
    qb = players[players.position == "QB"].iloc[0]
    mates = players[(players.team == qb.team) & players.position.isin(["WR", "TE"])]
    dst = players[players.position == "DST"].iloc[0]
    return {
        "QB + 1 WR/TE": len(mates) >= 1,
        "QB + 2 WR/TE": len(mates) >= 2,
        "bring-back (opposing player)": ((players.team == qb.opponent) & (players.position != "DST")).any(),
        "stack mate under $4,000": (mates.salary < 4000).any(),
        "DST facing its own players": ((players.team == dst.opponent) & (players.position != "DST")).any(),
        "two TEs": (players.position == "TE").sum() == 2,
        "players under $4,000": (players.salary < 4000).sum(),
        "salary used": players.salary.sum(),
    }


def predictions(tables: dict) -> pd.DataFrame:
    """Walk-forward predictions from 2018, with the live rules applied."""
    last = int(tables["player_logs"].year.max())
    players = F.player_features(
        tables["player_logs"], tables["games"], nflverse.snap_counts(last), tables["injuries"], tables["rosters"]
    )
    defenses = F.dst_features(tables["dst_logs"], tables["games"], nflverse.schedule())
    predicted = walk_forward(pd.concat([players, defenses], ignore_index=True), POSITIONS, list(range(2018, last + 1)), 2012)
    predicted.loc[predicted.ruled_out.eq(True), "model"] = 0.0
    qbs = predicted[(predicted.position == "QB") & ~predicted.ruled_out.eq(True)].copy()
    qbs["depth"] = qbs.groupby(["year", "week", "team"]).attempt_share_short.rank(
        ascending=False, method="first", na_option="bottom"
    )
    predicted.loc[qbs.index[qbs.depth > 1], "model"] = 0.0
    return predicted


def salary_weeks(tables: dict, predicted: pd.DataFrame) -> pd.DataFrame:
    """Pool rows with a salary, a FantasyPros projection and a prediction, in
    weeks whose games are all final."""
    pool = tables["pool"]
    pool = pool[pool.position.isin(POSITIONS) & pool.salary.notna() & pool.proj_fpts.notna()]
    keys = predicted[["year", "week", "gsis_id", "team", "opponent", "position", "model"]]
    players = pool[pool.position != "DST"].merge(
        keys[keys.position != "DST"].drop(columns="position"), on=["year", "week", "gsis_id"]
    )
    defenses = pool[pool.position == "DST"].merge(
        keys[keys.position == "DST"].drop(columns=["gsis_id", "position"]),
        left_on=["year", "week", "nfl_team"], right_on=["year", "week", "team"],
    )
    rows = pd.concat([players, defenses], ignore_index=True).drop_duplicates(["year", "week", "player", "position"])
    rows["actual"] = rows.actual_dk_points.fillna(0.0)
    rows["recent"] = rows.recent_avg.fillna(rows.proj_fpts)
    played = set(tables["dst_logs"].game_id)
    final = tables["games"].groupby(["year", "week"]).game_id.apply(lambda ids: set(ids) <= played)
    return rows.merge(final[final].reset_index()[["year", "week"]], on=["year", "week"])


def main() -> None:
    tables = data.load()
    weeks = salary_weeks(tables, predictions(tables))
    say("walk-forward done")

    scores, patterns = [], []
    for (year, week), pool in weeks.groupby(["year", "week"]):
        pool = pool.reset_index(drop=True)
        if (pool.position == "DST").sum() < 4 or (pool.position == "QB").sum() < 4:
            continue
        actual = pool.actual.to_numpy()
        projections = {
            "FantasyPros": pool.proj_fpts,
            "Our model": pool.model,
            "FP + model average": (pool.proj_fpts + pool.model) / 2,
            "FP 90/10": 0.9 * pool.proj_fpts + 0.1 * pool.recent,
            "FP 80/20": 0.8 * pool.proj_fpts + 0.2 * pool.recent,
            "Model 90/10": 0.9 * pool.model + 0.1 * pool.recent,
            "Model 80/20": 0.8 * pool.model + 0.2 * pool.recent,
        }
        row = {"year": year, "week": week}
        best = solve(pool, actual)
        row["Best in hindsight"] = actual[best].sum()
        row["Best in hindsight, rules"] = actual[solve(pool, actual, rules=True)].sum()
        for name, points in projections.items():
            for rules in (True, False):
                if not rules and name not in ("FantasyPros", "Our model"):
                    continue
                lineup = solve(pool, points.to_numpy(), rules)
                if lineup is not None:
                    row[name if rules else f"{name}, no rules"] = actual[lineup].sum()
        scores.append(row)
        patterns.append(describe(pool, best))

    scores = pd.DataFrame(scores).set_index(["year", "week"])
    first, last = scores.index.get_level_values(0).min(), scores.index.get_level_values(0).max()
    print(f"\n1. One lineup a week, {len(scores)} weeks ({first}-{last}), actual points:")
    base = scores["FantasyPros"]
    for name in scores.columns:
        difference = (scores[name] - base).dropna()
        margin = 1.96 * difference.std() / np.sqrt(len(difference)) if len(difference) > 1 else 0.0
        print(
            f"  {name:<26} average {scores[name].mean():6.1f}, vs FantasyPros {difference.mean():+6.1f} (±{margin:.1f}), "
            f"beats it {(scores[name] > base).mean():4.0%} of weeks, {(scores[name] / scores['Best in hindsight']).mean():4.0%} of the best"
        )

    patterns = pd.DataFrame(patterns)
    print("\n2. The best lineup in hindsight, with no rules:")
    for name, value in patterns.mean().items():
        print(f"  {name:<30} {value:.0%}" if patterns[name].dtype == bool else f"  {name:<30} {value:,.1f} on average")
    cost = scores["Best in hindsight"] - scores["Best in hindsight, rules"]
    print(f"  The rules would have cost it {cost.mean():.1f} points a week (median {cost.median():.1f}, most {cost.max():.1f})")


if __name__ == "__main__":
    main()
