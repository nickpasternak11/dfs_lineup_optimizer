"""Score props-based projections on the season the props file covers,
against FantasyPros, the model and the recent-average baseline.

Everything fitted (the anytime-TD margin, the model + props blend weight)
is fitted on the season's first half of weeks and judged on the second, so
no number is scored on the weeks that set it.
"""

import numpy as np
import pandas as pd
from dfs_common import accuracy

from src import props
from src.backtest import attach_predictions
from src.features import SHORT_HALFLIFE, _history, _order

POSITIONS = ["QB", "RB", "WR", "TE"]
STATS = ["passing_yards", "passing_tds", "interceptions", "rushing_yards", "receptions", "receiving_yards", "scoring_tds"]
SOURCES = ["projection", "recent_avg", "model", "props", "model_props", "fp_props"]
LABELS = {
    "projection": "FantasyPros",
    "recent_avg": "Recent avg",
    "model": "Model",
    "props": "Props",
    "model_props": "Model+props",
    "fp_props": "FP+props (diagnostic)",
}


def recent_stats(logs: pd.DataFrame) -> pd.DataFrame:
    """Each player's recent averages going into each game (earlier games
    only), for markets the books didn't post, and their actual scoring TDs."""
    df = logs[logs.season_type == "REG"].copy()
    df["scoring_tds"] = df.rushing_tds + df.receiving_tds
    df["t"] = _order(df)
    df = df.sort_values(["gsis_id", "t"]).reset_index(drop=True)
    history = _history(df, "gsis_id", STATS, {"recent": SHORT_HALFLIFE})
    history.columns = [c.removesuffix("_recent") for c in history.columns]
    return pd.concat([df[["year", "week", "gsis_id"]], history.add_prefix("hist_"), df[["scoring_tds"]].rename(columns={"scoring_tds": "actual_tds"})], axis=1)


def best_weight(df: pd.DataFrame, a: str, b: str) -> float:
    """The weight on `a` in w*a + (1-w)*b with the lowest average miss."""
    grid = np.linspace(0, 1, 21)
    misses = [((w * df[a] + (1 - w) * df[b]) - df.actual).abs().mean() for w in grid]
    return float(grid[int(np.argmin(misses))])


def run(tables: dict, predictions: pd.DataFrame, quotes: pd.DataFrame, min_proj: float = 5.0) -> str:
    quotes = props.attach_games(quotes, tables["games"])
    season = int(quotes.year.mode()[0])
    logs = tables["player_logs"]
    shapes = props.gamma_shapes(logs[logs.year < season])
    expected = props.expected_stats(quotes, shapes)

    pool = tables["pool"]
    pool = pool[(pool.year == season) & pool.position.isin(POSITIONS)]
    pool = attach_predictions(pool, predictions)
    matched = props.match_players(expected, pool)
    matched = matched.merge(recent_stats(logs), on=["year", "week", "gsis_id"], how="left")
    history = matched[[f"hist_{c}" for c in STATS]].rename(columns=lambda c: c.removeprefix("hist_"))

    weeks = sorted(matched.week.unique())
    split = weeks[len(weeks) // 2 - 1]
    first = matched.week <= split
    priced = first & matched.td_price_probability.notna() & matched.actual_tds.notna()
    hold = props.fit_td_hold(matched.loc[priced, "td_price_probability"], matched.loc[priced, "actual_tds"])
    matched["props"] = props.dk_points(matched, history, hold).where(props.has_core_market(matched))

    df = matched.rename(columns={"proj_fpts": "projection", "actual_dk_points": "actual"})
    base = ["projection", "recent_avg", "model", "props"]
    df = df[df.actual.notna() & df[base].notna().all(axis=1) & (df[base].max(axis=1) >= min_proj)].copy()
    fit = df[df.week <= split]
    w_model = best_weight(fit, "model", "props")
    w_fp = best_weight(fit, "projection", "props")
    df["model_props"] = w_model * df.model + (1 - w_model) * df.props
    df["fp_props"] = w_fp * df.projection + (1 - w_fp) * df.props

    lines = [
        f"Props backtest, {season}: {len(df):,} player-weeks (weeks {weeks[0]}-{weeks[-1]}) with "
        "a FantasyPros projection, a model prediction and a props projection",
        f"Fitted on weeks {weeks[0]}-{split}: anytime-TD margin {hold:.1%}; "
        f"blend weights: model {w_model:.2f} / props {1 - w_model:.2f}, FP {w_fp:.2f} / props {1 - w_fp:.2f}",
        f"Gamma shapes (from earlier seasons): " + ", ".join(f"{k} {v:.2f}" for k, v in shapes.items()),
        "",
    ]
    for title, subset in (("Weeks the fits never saw", df[df.week > split]), ("Whole season", df)):
        groups = {s: accuracy.group_rank_correlations(subset, s) for s in SOURCES}
        lines.append(f"{title} ({len(subset):,} player-weeks): average miss / ranking / bias")
        cards = [("All", accuracy.scorecard(subset, SOURCES, groups))]
        for position in POSITIONS:
            part = subset[subset.position == position]
            if not part.empty:
                cards.append((position, accuracy.scorecard(part, SOURCES, {s: g[g.position == position] for s, g in groups.items()})))
        for label, card in cards:
            cells = []
            for source in SOURCES:
                m = card["metrics"][source]
                rank = "-" if m["rank_corr"] is None else f"{m['rank_corr']:.3f}"
                cells.append(f"{LABELS[source]} {m['mae']:.2f}/{rank}/{m['bias']:+.2f}")
            lines.append(f"  {label:<4} n={card['player_weeks']:>5}  " + "  ".join(cells))
        lines.append("")
    return "\n".join(lines)
