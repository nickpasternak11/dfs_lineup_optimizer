"""`python main.py backtest`: train the projection model season by season
and score it against FantasyPros' projection on the accuracy page's rows.
Reads the database; writes nothing."""

import argparse

import pandas as pd

from src import backtest, data, nflverse
from src.configs import FIRST_TEST_SEASON, FIRST_TRAIN_SEASON, POSITIONS, log
from src.features import dst_features, player_features
from src.model import walk_forward


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DraftKings projection model")
    parser.add_argument("command", nargs="?", default="backtest", choices=["backtest"])
    parser.add_argument("--first-test-season", type=int, default=FIRST_TEST_SEASON)
    parser.add_argument("--first-train-season", type=int, default=FIRST_TRAIN_SEASON)
    return parser.parse_args()


def run_backtest(args: argparse.Namespace) -> None:
    log.info("Loading game logs..")
    tables = data.load()
    snaps = nflverse.snap_counts(int(tables["player_logs"].year.max()))
    features = pd.concat(
        [
            player_features(tables["player_logs"], tables["games"], snaps),
            dst_features(tables["dst_logs"], tables["games"], nflverse.schedule()),
        ],
        ignore_index=True,
    )
    last_season = int(features.year.max())
    seasons = list(range(args.first_test_season, last_season + 1))
    log.info("Training on %s+ and predicting %s-%s..", args.first_train_season, seasons[0], seasons[-1])
    predictions = walk_forward(features, POSITIONS, seasons, args.first_train_season)
    rows = backtest.comparison_rows(backtest.attach_predictions(tables["pool"], predictions))
    print(backtest.format_report(rows))


if __name__ == "__main__":
    args = parse_args()
    run_backtest(args)
