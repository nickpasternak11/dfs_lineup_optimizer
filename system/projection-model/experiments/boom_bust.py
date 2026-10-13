"""How well can we predict boom and bust? (#51)

Walk-forward over 2018 on: each season's projections, and everything fitted
on them, come only from earlier seasons. For each DraftKings pool player-week
it estimates the chance of four events with three methods and scores them.

Events:
- 20+ points
- 4x salary (20 points on a $5,000 player)
- boom: our projection beaten by 10+
- bust: falling 5+ short of our projection

Methods:
- A, baseline: our projection plus the typical miss, from earlier seasons'
  out-of-sample misses at the same position and projection range.
- B, spread model: a second model predicts each player's expected miss size
  from the same features; misses are scaled by it.
- C, classifier: a boosted logistic classifier for P(points >= X), with X an
  input, trained on thresholds 5 to 40.

Prints Brier score, log loss, AUC and calibration for each. Reads the
database, writes nothing; a few minutes. Results from 2026-10-12 are on #51:
the projection explains nearly all of P(20+); booms are barely predictable.

    make experiment NAME=boom_bust
"""

import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score
from src import data, nflverse
from src import features as F
from src.model import walk_forward

warnings.simplefilter("ignore")

POSITIONS = ["QB", "RB", "WR", "TE"]
FIRST_EVALUATED = 2018
PROJECTION_RANGES = [-np.inf, 5, 10, 15, 20, 25, np.inf]
CLASSIFIER_THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40]
METHODS = ["A baseline", "B spread model", "C classifier"]
# Event -> column holding its cut; "bust" counts points below the cut.
EVENTS = {"20+ points": "x_20", "4x salary": "x_4x", "boom: projection +10": "x_boom", "bust: projection -5": "x_bust"}
START = time.time()


def say(*parts):
    print(f"[{time.time() - START:5.0f}s]", *parts, flush=True)


def share_at_least(sorted_values: np.ndarray, cut: np.ndarray) -> np.ndarray:
    """Share of sorted_values >= each cut."""
    return 1 - np.searchsorted(sorted_values, cut, side="left") / len(sorted_values)


def evaluation_rows(pool: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Pool player-weeks with a salary, linked to their game's prediction, as on
    the accuracy page (either source projected 5 or more)."""
    pool = pool[pool.position.isin(POSITIONS) & pool.actual_dk_points.notna() & pool.salary.notna()]
    rows = pool[["year", "week", "gsis_id", "salary", "proj_fpts"]].merge(
        predictions[predictions.year >= FIRST_EVALUATED], on=["year", "week", "gsis_id"]
    )
    rows = rows[rows[["model", "proj_fpts"]].max(axis=1) >= 5].reset_index(drop=True)
    return rows.assign(
        x_20=20.0, x_4x=4 * rows.salary / 1000, x_boom=rows.model + 10, x_bust=rows.model - 5
    )


def estimate(train: pd.DataFrame, rows: pd.DataFrame, position: str) -> dict[str, dict[str, np.ndarray]]:
    """Each method's P(points >= cut) for each event, for one position's rows."""
    out = {method: {} for method in METHODS}

    # A: the typical miss for this position and projection range.
    for event, column in EVENTS.items():
        probability = np.empty(len(rows))
        for bucket in range(len(PROJECTION_RANGES) - 1):
            selected = (rows.bucket == bucket).to_numpy()
            if not selected.any():
                continue
            misses = np.sort(train.resid[train.bucket == bucket].to_numpy())
            if len(misses) < 50:
                misses = np.sort(train.resid.to_numpy())
            cut = (rows[column] - rows.model).to_numpy()[selected]
            probability[selected] = share_at_least(misses, cut)
        out["A baseline"][event] = probability

    # B: misses scaled by a model of each player's expected miss size.
    columns = F.feature_columns(position) + ["model"]
    spread = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, random_state=0
    ).fit(train[columns], train.resid.abs())
    scaled = np.sort((train.resid / np.clip(spread.predict(train[columns]), 1.0, None)).to_numpy())
    row_spread = np.clip(spread.predict(rows[columns]), 1.0, None)
    for event, column in EVENTS.items():
        out["B spread model"][event] = share_at_least(scaled, ((rows[column] - rows.model) / row_spread).to_numpy())

    # C: one classifier over stacked thresholds; P falls as the threshold rises.
    stacked = pd.concat(
        [train[columns + ["dk_points"]].assign(threshold=t) for t in CLASSIFIER_THRESHOLDS], ignore_index=True
    )
    stacked["gap"] = stacked.threshold - stacked.model
    inputs = columns + ["threshold", "gap"]
    classifier = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=300,
        monotonic_cst=[0] * len(columns) + [-1, -1], random_state=0,
    ).fit(stacked[inputs], (stacked.dk_points >= stacked.threshold).astype(int))
    for event, column in EVENTS.items():
        query = rows[columns].assign(threshold=rows[column].to_numpy(), gap=(rows[column] - rows.model).to_numpy())
        out["C classifier"][event] = classifier.predict_proba(query[inputs])[:, 1]
    return out


def score(probability: np.ndarray, happened: np.ndarray) -> dict[str, float]:
    p = np.clip(probability, 1e-4, 1 - 1e-4)
    return {
        "brier": float(np.mean((p - happened) ** 2)),
        "log_loss": float(-np.mean(happened * np.log(p) + (1 - happened) * np.log(1 - p))),
        "auc": float(roc_auc_score(happened, p)),
    }


def main() -> None:
    tables = data.load()
    last = int(tables["player_logs"].year.max())
    features = F.player_features(
        tables["player_logs"], tables["games"], nflverse.snap_counts(last), tables["injuries"], tables["rosters"]
    )
    predictions = walk_forward(features, POSITIONS, list(range(2013, last + 1)), 2012)
    predictions["resid"] = predictions.dk_points - predictions.model
    predictions["bucket"] = pd.cut(predictions.model, PROJECTION_RANGES, labels=False)
    rows = evaluation_rows(tables["pool"], predictions)
    say(f"walk-forward done; {len(rows):,} pool player-weeks to score")

    probabilities = {method: {event: np.full(len(rows), np.nan) for event in EVENTS} for method in METHODS}
    for season in sorted(rows.year.unique()):
        train = predictions[(predictions.year < season) & (predictions.year >= 2013)]
        for position in POSITIONS:
            index = rows.index[(rows.year == season) & (rows.position == position)].to_numpy()
            if len(index):
                estimates = estimate(train[train.position == position], rows.loc[index], position)
                for method, events in estimates.items():
                    for event, values in events.items():
                        probabilities[method][event][index] = values
        say("season", season)
    for method in METHODS:
        probabilities[method]["bust: projection -5"] = 1 - probabilities[method]["bust: projection -5"]

    print(f"\n{len(rows):,} pool player-weeks, {FIRST_EVALUATED}-{last}")
    for event, column in EVENTS.items():
        below = event.startswith("bust")
        happened = ((rows.dk_points < rows[column]) if below else (rows.dk_points >= rows[column])).to_numpy().astype(float)
        none = score(np.full(len(happened), happened.mean()), happened)
        print(f"\n{event}: happened {happened.mean():.1%} of the time")
        print(f"  {'method':<16} {'Brier':>7} {'log loss':>9} {'AUC':>6}")
        print(f"  {'no information':<16} {none['brier']:7.4f} {none['log_loss']:9.4f} {'-':>6}")
        for method in METHODS:
            s = score(probabilities[method][event], happened)
            print(f"  {method:<16} {s['brier']:7.4f} {s['log_loss']:9.4f} {s['auc']:6.3f}")
        for method in METHODS:
            p = probabilities[method][event]
            bins = pd.cut(p, [0, 0.05, 0.1, 0.2, 0.3, 0.5, 1.01], right=False)
            table = pd.DataFrame({"p": p, "y": happened}).groupby(bins, observed=True).agg(
                n=("y", "size"), predicted=("p", "mean"), actual=("y", "mean")
            )
            print(f"    {method} calibration: " + "; ".join(
                f"{r.predicted:.0%} predicted, {r.actual:.0%} happened (n={r.n})" for _, r in table.iterrows()
            ))
        print("    AUC by position (A/B/C): " + " | ".join(
            f"{position} " + "/".join(
                f"{roc_auc_score(happened[(rows.position == position).to_numpy()], probabilities[m][event][(rows.position == position).to_numpy()]):.3f}"
                for m in METHODS
            )
            for position in POSITIONS
        ))


if __name__ == "__main__":
    main()
