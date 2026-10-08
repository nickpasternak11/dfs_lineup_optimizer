"""The projection model's commands:

- `predict`: project this week's pool players whose games are still to come
  and store the snapshot in model_projections (the orchestrator's daily job).
- `lineups`: save the optimizer's suggested lineups on each projection
  source for this week's games still to come, for the weekly review. The
  orchestrator runs it every morning with --on-first-game-day, so it saves
  once a week, before the first game, and Sunday at 11:50 AM ET with
  --late-swap, which keeps each saved lineup's players whose games have
  started and re-optimizes the rest.
- `backtest`: train season by season and score against FantasyPros on the
  accuracy page's rows. Reads only.
- `props`: score player props on the season an Odds API export covers.
"""

import argparse
from datetime import datetime, timezone

import pandas as pd
from dfs_common.season import current_season_year

from src import backtest, data, lineups, nflverse, predict, props_backtest
from src.configs import FIRST_TEST_SEASON, FIRST_TRAIN_SEASON, POSITIONS, log
from src.features import dst_features, player_features
from src.model import walk_forward


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DraftKings projection model")
    parser.add_argument("command", nargs="?", default="backtest", choices=["predict", "lineups", "backtest", "props"])
    parser.add_argument("--year", type=int, help="predict, lineups: season (default: current)")
    parser.add_argument("--week", type=int, help="predict, lineups: week (default: the latest in the pool)")
    parser.add_argument("--dry-run", action="store_true", help="predict, lineups: print instead of storing")
    parser.add_argument(
        "--on-first-game-day",
        action="store_true",
        help="lineups: save only on the day of the week's first game, and only once a week",
    )
    parser.add_argument(
        "--late-swap",
        action="store_true",
        help="lineups: re-optimize the saved lineups' players whose games haven't started (once a week)",
    )
    parser.add_argument(
        "--props-file",
        default="/props/player_props_2024_through_w15.csv",
        help="props: an Odds API player-props export (one season)",
    )
    parser.add_argument("--first-test-season", type=int, default=FIRST_TEST_SEASON)
    parser.add_argument("--first-train-season", type=int, default=FIRST_TRAIN_SEASON)
    return parser.parse_args()


def build_features(tables: dict) -> pd.DataFrame:
    snaps = nflverse.snap_counts(int(tables["player_logs"].year.max()))
    return pd.concat(
        [
            player_features(tables["player_logs"], tables["games"], snaps, tables["injuries"]),
            dst_features(tables["dst_logs"], tables["games"], nflverse.schedule()),
        ],
        ignore_index=True,
    )


def run_predict(args: argparse.Namespace) -> None:
    now = datetime.now(timezone.utc)
    year = args.year or current_season_year()
    week = args.week or data.latest_pool_week(year)
    if week is None:
        log.info("No %s pool yet; nothing to project", year)
        return
    pool = data.load_pool_week(year, week)
    tables = data.load(accuracy_rows=False)
    snaps = nflverse.snap_counts(int(tables["player_logs"].year.max()))
    log.info("Projecting %s week %s (%s pool players)..", year, week, len(pool))
    projections = predict.predict_week(tables, pool, year, week, now, snaps, nflverse.schedule())
    if projections.empty:
        log.info("Every %s week %s game has kicked off; nothing to project", year, week)
        return
    if args.dry_run:
        print(projections.sort_values("proj_dk_points", ascending=False).to_string(index=False))
        return
    predict.store(projections)


def run_lineups(args: argparse.Namespace) -> None:
    now = datetime.now(timezone.utc)
    year = args.year or current_season_year()
    week = args.week or data.latest_pool_week(year)
    if week is None:
        log.info("No %s pool yet; no lineups to save", year)
        return
    if args.late_swap:
        save_late_swap(year, week, now, args.dry_run)
        return
    if args.on_first_game_day:
        first = data.first_kickoff(year, week)
        if not lineups.is_first_game_day(first, now):
            log.info("%s week %s starts %s; not saving lineups today", year, week, first)
            return
        if data.has_saved_lineups(year, week):
            log.info("%s week %s lineups are already saved", year, week)
            return
    suggested = lineups.suggested_lineups(year, week)
    rows = lineups.snapshot_rows(suggested, lineups.pool_projections(year, week), year, week, now)
    if rows.empty:
        log.info("No lineups for %s week %s", year, week)
        return
    if args.dry_run:
        print(rows.to_string(index=False))
        return
    lineups.store(rows)


def save_late_swap(year: int, week: int, now: datetime, dry_run: bool) -> None:
    if not data.has_saved_lineups(year, week, "initial"):
        log.info("No %s week %s lineups saved before its first game; nothing to swap", year, week)
        return
    if data.has_saved_lineups(year, week, "late_swap") and not dry_run:
        log.info("%s week %s late swap is already saved", year, week)
        return
    pool = lineups.pool_projections(year, week)
    swapped = lineups.late_swap_lineups(
        lineups.late_swap_requests(data.load_initial_lineups(year, week), pool, year, week, now)
    )
    rows = lineups.snapshot_rows(swapped, pool, year, week, now, phase="late_swap")
    if rows.empty:
        log.info("No late swap for %s week %s", year, week)
    elif dry_run:
        print(rows.to_string(index=False))
    else:
        lineups.store(rows)


def run_props(args: argparse.Namespace) -> None:
    """Props projections for the file's season against FantasyPros and the
    model (trained on the seasons before it)."""
    tables = data.load()
    quotes = pd.read_csv(args.props_file)
    season = int(pd.to_datetime(quotes.commence_time, utc=True).dt.year.mode()[0])
    predictions = walk_forward(build_features(tables), POSITIONS, [season], args.first_train_season)
    print(props_backtest.run(tables, predictions, quotes))


def run_backtest(args: argparse.Namespace) -> None:
    log.info("Loading game logs..")
    tables = data.load()
    features = build_features(tables)
    last_season = int(features.year.max())
    seasons = list(range(args.first_test_season, last_season + 1))
    log.info("Training on %s+ and predicting %s-%s..", args.first_train_season, seasons[0], seasons[-1])
    predictions = walk_forward(features, POSITIONS, seasons, args.first_train_season)
    rows = backtest.comparison_rows(backtest.attach_predictions(tables["pool"], predictions))
    print(backtest.format_report(rows))


if __name__ == "__main__":
    args = parse_args()
    commands = {"predict": run_predict, "lineups": run_lineups, "backtest": run_backtest, "props": run_props}
    commands[args.command](args)
