"""Do teammates' results move together, does simulating that predict lineup
totals better, and which single lineup clears high scores? (#51, #6)

Walk-forward: each season uses projections, misses and correlations from
earlier seasons only.

1. Correlation of players' misses against our projection, as normal scores
   within position and projection range, for pairs in the same game: same
   team or opponents, by position pair (2013 on).
2. For every week with DraftKings salaries and every game final, simulate
   the week's outcomes (projection plus the typical miss, with and without
   those correlations) and ask candidate lineups for P(clearing a high bar):
   the 95th percentile of the most-projected lineup's simulated total.
   Candidates are the best lineup in each of a few simulated weeks.
3. One lineup per week from each strategy, scored on actual points: the most
   projected points, the same with a QB + 2 pass-catcher stack, and the
   candidate each simulation gives the best chance of clearing the bar.

Reads the database, writes nothing; a few minutes. Results from 2026-10-12
are on #51: correlations are real (QB with his WR/TE about +0.2, a defense
against the opposing QB about -0.3), but over 45 weeks nothing beat the most
projected lineup on average, and the tail can't be measured.

    make experiment NAME=lineup_simulation
"""

import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import Bounds, LinearConstraint, milp
from src import data, nflverse
from src import features as F
from src.model import walk_forward

warnings.simplefilter("ignore")

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]
PROJECTION_RANGES = [-np.inf, 5, 10, 15, 20, 25, np.inf]
SALARY_CAP = 50000
ROSTER = {"QB": (1, 1), "RB": (2, 3), "WR": (3, 4), "TE": (1, 2), "DST": (1, 1)}
DRAWS = 2000
CANDIDATE_DRAWS = 150
HIGH_BAR = 0.95
START = time.time()
rng = np.random.default_rng(0)


def say(*parts):
    print(f"[{time.time() - START:5.0f}s]", *parts, flush=True)


def pair_correlations(history: pd.DataFrame) -> pd.DataFrame:
    """Correlation of normal-score misses by (side, position, position), side
    "same" for teammates and "opp" for opponents. Players projected under 4
    are left out; they're rarely in a lineup."""
    relevant = history[(history.model >= 4) | (history.position == "DST")]
    relevant = relevant[["year", "week", "team", "opponent", "position", "u"]].reset_index(drop=True)
    relevant = relevant.reset_index().rename(columns={"index": "i"})
    same = relevant.merge(relevant, on=["year", "week", "team"], suffixes=("_a", "_b"))
    opposing = relevant.merge(
        relevant, left_on=["year", "week", "team"], right_on=["year", "week", "opponent"], suffixes=("_a", "_b")
    )
    pairs = pd.concat(
        [same[same.i_a < same.i_b].assign(side="same"), opposing[opposing.i_a < opposing.i_b].assign(side="opp")],
        ignore_index=True,
    )
    a, b = pairs.position_a, pairs.position_b
    pairs["pa"], pairs["pb"] = np.where(a <= b, a, b), np.where(a <= b, b, a)
    return (
        pairs.groupby(["side", "pa", "pb"])
        .apply(lambda g: pd.Series({"r": np.corrcoef(g.u_a, g.u_b)[0, 1], "pairs": len(g)}))
        .reset_index()
    )


def solve(pool: pd.DataFrame, points: np.ndarray, stack: int = 0) -> np.ndarray | None:
    """The DraftKings classic lineup (row positions) with the most `points`;
    with `stack`, its QB has at least that many of his own WRs and TEs."""
    position = pool.position.to_numpy()
    rows, low, high = [np.ones(len(pool)), pool.salary.to_numpy(float)], [9, 0], [9, SALARY_CAP]
    for name, (a, b) in ROSTER.items():
        rows.append((position == name).astype(float))
        low.append(a)
        high.append(b)
    if stack:
        team = pool.team.to_numpy()
        for qb in np.flatnonzero(position == "QB"):
            coefficients = ((team == team[qb]) & np.isin(position, ["WR", "TE"])).astype(float)
            coefficients[qb] = -stack
            rows.append(coefficients)
            low.append(0)
            high.append(np.inf)
    result = milp(
        -points, constraints=LinearConstraint(np.array(rows), low, high),
        integrality=np.ones(len(pool)), bounds=Bounds(0, 1), options={"time_limit": 20},
    )
    return None if result.x is None else np.flatnonzero(result.x > 0.5)


def simulate(pool: pd.DataFrame, correlations: pd.DataFrame | None, misses: dict, fallback: dict) -> np.ndarray:
    """DRAWS simulated weeks (draws x players): each player's projection plus
    a miss drawn from his position and projection range, correlated within
    games when `correlations` is given (a Gaussian copula)."""
    n = len(pool)
    matrix = np.eye(n)
    if correlations is not None:
        lookup = {(r.side, r.pa, r.pb): r.r for r in correlations.itertuples()}
        team, opponent, position = pool.team.to_numpy(), pool.opponent.to_numpy(), pool.position.to_numpy()
        for i in range(n):
            for j in range(i + 1, n):
                side = "same" if team[i] == team[j] else ("opp" if opponent[i] == team[j] else None)
                if side:
                    pa, pb = sorted((position[i], position[j]))
                    matrix[i, j] = matrix[j, i] = lookup.get((side, pa, pb), 0.0)
        values, vectors = np.linalg.eigh(matrix)
        matrix = (vectors * np.clip(values, 1e-6, None)) @ vectors.T
        scale = np.sqrt(np.diag(matrix))
        matrix = matrix / np.outer(scale, scale)
    quantile = stats.norm.cdf(rng.standard_normal((DRAWS, n)) @ np.linalg.cholesky(matrix).T)
    out = np.empty((DRAWS, n))
    for k, (position, bucket, projection) in enumerate(zip(pool.position, pool.bucket, pool.model)):
        sorted_misses = misses.get((position, bucket))
        if sorted_misses is None or len(sorted_misses) < 50:
            sorted_misses = fallback[position]
        index = np.minimum((quantile[:, k] * len(sorted_misses)).astype(int), len(sorted_misses) - 1)
        out[:, k] = projection + sorted_misses[index]
    return out


def salary_weeks(tables: dict, predictions: pd.DataFrame) -> pd.DataFrame:
    """Pool rows with a salary and a prediction, in weeks whose games are all
    final (every game has its team stats)."""
    pool = tables["pool"]
    pool = pool[pool.position.isin(POSITIONS) & pool.salary.notna()].assign(actual=lambda d: d.actual_dk_points.fillna(0.0))
    keys = predictions[["year", "week", "gsis_id", "team", "opponent", "position", "model", "bucket"]]
    players = pool[pool.position != "DST"].merge(
        keys[keys.position != "DST"].drop(columns="position"), on=["year", "week", "gsis_id"]
    )
    defenses = pool[pool.position == "DST"].merge(
        keys[keys.position == "DST"].drop(columns=["gsis_id", "position"]),
        left_on=["year", "week", "nfl_team"], right_on=["year", "week", "team"],
    )
    rows = pd.concat([players, defenses], ignore_index=True).drop_duplicates(["year", "week", "player", "position"])
    played = set(tables["dst_logs"].game_id)
    final = tables["games"].groupby(["year", "week"]).game_id.apply(lambda ids: set(ids) <= played)
    final = final[final].reset_index()[["year", "week"]]
    return rows.merge(final, on=["year", "week"])


def main() -> None:
    tables = data.load()
    last = int(tables["player_logs"].year.max())
    players = F.player_features(
        tables["player_logs"], tables["games"], nflverse.snap_counts(last), tables["injuries"], tables["rosters"]
    )
    defenses = F.dst_features(tables["dst_logs"], tables["games"], nflverse.schedule())
    predictions = walk_forward(pd.concat([players, defenses], ignore_index=True), POSITIONS, list(range(2013, last + 1)), 2012)
    predictions["resid"] = predictions.dk_points - predictions.model
    predictions["bucket"] = pd.cut(predictions.model, PROJECTION_RANGES, labels=False)
    predictions["u"] = predictions.groupby(["position", "bucket"]).resid.transform(
        lambda r: stats.norm.ppf((r.rank(method="average") - 0.5) / len(r))
    )
    say("walk-forward done")

    correlations = pair_correlations(predictions[predictions.year < last])
    print(f"\n1. How players' misses move together (2013-{last - 1}):")
    print(
        correlations[correlations.pairs >= 500]
        .sort_values(["side", "r"], ascending=[False, False])
        .to_string(index=False, float_format=lambda v: f"{v:.3f}")
    )

    weeks = salary_weeks(tables, predictions)
    results, calibration = [], []
    for season in sorted(weeks.year.unique()):
        history = predictions[predictions.year < season]
        season_correlations = pair_correlations(history)
        season_correlations = season_correlations[season_correlations.pairs >= 200]
        misses = {key: np.sort(g.resid.to_numpy()) for key, g in history.groupby(["position", "bucket"])}
        fallback = {position: np.sort(g.resid.to_numpy()) for position, g in history.groupby("position")}
        for week in sorted(weeks[weeks.year == season].week.unique()):
            pool = weeks[(weeks.year == season) & (weeks.week == week)].reset_index(drop=True)
            if (pool.position == "DST").sum() < 2 or (pool.position == "QB").sum() < 2:
                continue
            actual = pool.actual.to_numpy()
            best = solve(pool, actual)
            most_projected = solve(pool, pool.model.to_numpy())
            stacked = solve(pool, pool.model.to_numpy(), stack=2)
            sims = {
                "correlated": simulate(pool, season_correlations, misses, fallback),
                "independent": simulate(pool, None, misses, fallback),
            }
            candidates = {tuple(most_projected)} | ({tuple(stacked)} if stacked is not None else set())
            for sim in sims.values():
                for draw in range(CANDIDATE_DRAWS):
                    lineup = solve(pool, sim[draw])
                    if lineup is not None:
                        candidates.add(tuple(lineup))
            candidates = [np.array(c) for c in candidates]
            bar = np.quantile(sims["correlated"][:, most_projected].sum(axis=1), HIGH_BAR)
            chance = {kind: np.array([(s[:, c].sum(axis=1) >= bar).mean() for c in candidates]) for kind, s in sims.items()}
            for k, lineup in enumerate(candidates):
                calibration.append({
                    "cleared": actual[lineup].sum() >= bar,
                    "correlated": chance["correlated"][k], "independent": chance["independent"][k],
                })
            picks = {
                "most projected points": most_projected,
                "most projected, QB + 2 stack": stacked,
                "simulation pick (correlated)": candidates[int(np.argmax(chance["correlated"]))],
                "simulation pick (independent)": candidates[int(np.argmax(chance["independent"]))],
            }
            for strategy, lineup in picks.items():
                if lineup is not None:
                    results.append({"year": season, "week": week, "strategy": strategy,
                                    "actual": actual[lineup].sum(), "of_best": actual[lineup].sum() / actual[best].sum()})
            say(season, week, f"{len(pool)} players, {len(candidates)} candidates")

    calibration = pd.DataFrame(calibration)
    cleared = calibration.cleared.to_numpy().astype(float)
    print(f"\n2. P(a lineup clears the week's high bar): {len(calibration):,} candidate lineups, {cleared.mean():.1%} cleared it")
    for kind in ["correlated", "independent"]:
        p = np.clip(calibration[kind].to_numpy(), 1e-4, 1 - 1e-4)
        log_loss = -np.mean(cleared * np.log(p) + (1 - cleared) * np.log(1 - p))
        table = pd.DataFrame({"p": p, "y": cleared}).groupby(pd.cut(p, [0, 0.02, 0.05, 0.1, 0.2, 1.0]), observed=True).agg(
            n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean")
        )
        print(f"  {kind}: Brier {np.mean((p - cleared) ** 2):.4f}, log loss {log_loss:.4f}; " + "; ".join(
            f"{r.predicted:.1%} predicted, {r.actual:.1%} happened (n={r.n})" for _, r in table.iterrows()
        ))

    scores = pd.DataFrame(results).pivot_table(index=["year", "week"], columns="strategy", values="actual")
    top = scores.max(axis=1)
    ties = scores.eq(top, axis=0).sum(axis=1)
    base = scores["most projected points"]
    print(f"\n3. One lineup a week, {len(scores)} weeks (actual points):")
    for strategy in scores.columns:
        difference = (scores[strategy] - base).dropna()
        margin = 1.96 * difference.std() / np.sqrt(len(difference)) if len(difference) > 1 else 0.0
        highest = (scores[strategy].eq(top) / ties).sum()
        print(f"  {strategy:<30} average {scores[strategy].mean():6.1f}, vs most projected "
              f"{difference.mean():+5.1f} (±{margin:.1f}), highest of the four in {highest:.1f} weeks (ties split)")


if __name__ == "__main__":
    main()
