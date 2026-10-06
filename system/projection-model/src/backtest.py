"""Score the model's walk-forward predictions against FantasyPros'
projection and the recent-average baseline, on the accuracy page's rows."""

import pandas as pd
from dfs_common import accuracy

SOURCES = ["projection", "recent_avg", "model"]
# Not a candidate: an average of the model and FantasyPros, to show whether
# the model knows something FantasyPros doesn't (the blend beats both if so).
DIAGNOSTIC = "blend"
LABELS = {
    "projection": "FantasyPros",
    "recent_avg": "Recent avg",
    "model": "Model",
    "blend": "Model+FP blend",
}


def attach_predictions(pool: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Pool rows with the model's prediction for the same game: players by
    gsis_id, defenses by team."""
    players = predictions[predictions.position != "DST"][["year", "week", "gsis_id", "model"]]
    dsts = predictions[predictions.position == "DST"][["year", "week", "team", "model"]]
    out = pool.merge(players, on=["year", "week", "gsis_id"], how="left")
    out = out.merge(
        dsts.rename(columns={"team": "nfl_team", "model": "dst_model"}),
        on=["year", "week", "nfl_team"],
        how="left",
    )
    is_dst = out.position == "DST"
    out.loc[is_dst, "model"] = out.loc[is_dst, "dst_model"]
    return out.drop(columns="dst_model")


def comparison_rows(pool: pd.DataFrame, min_proj: float = 5.0) -> pd.DataFrame:
    """Scored rows where every source has a value, counted when any source
    projected min_proj or more (as on the accuracy page)."""
    df = pool.rename(columns={"proj_fpts": "projection", "actual_dk_points": "actual"})
    df = df[df.actual.notna() & df[SOURCES].notna().all(axis=1)]
    df = df[df[SOURCES].max(axis=1) >= min_proj].copy()
    df[DIAGNOSTIC] = (df.projection + df.model) / 2
    return df


def scorecards(df: pd.DataFrame, by: str | None = None) -> list[tuple[str, dict]]:
    sources = SOURCES + [DIAGNOSTIC]
    groups = {s: accuracy.group_rank_correlations(df, s) for s in sources}
    if by is None:
        return [("All", accuracy.scorecard(df, sources, groups))]
    cards = []
    for value, subset in df.groupby(by):
        narrowed = {s: g[g[by] == value] for s, g in groups.items()} if by in accuracy.RANK_GROUPS else None
        cards.append((str(value), accuracy.scorecard(subset, sources, narrowed)))
    return cards


def format_report(df: pd.DataFrame) -> str:
    sources = SOURCES + [DIAGNOSTIC]
    lines = [
        f"{len(df):,} player-weeks, {df.year.min()}-{df.year.max()}, where every source "
        "projected someone for 5+ FPTS (the accuracy page's rows)",
        "",
    ]
    metrics = [("mae", "Avg miss", "{:.2f}"), ("rank_corr", "Ranking", "{:.3f}"), ("bias", "Bias", "{:+.2f}")]
    for title, by in (("Overall", None), ("By position", "position"), ("By season", "year")):
        lines.append(title)
        header = f"{'':<8}{'n':>7}  " + "  ".join(
            f"{name + ' ' + LABELS[s]:>22}" for _, name, _ in metrics for s in sources
        )
        lines.append(header)
        for label, card in scorecards(df, by):
            cells = []
            for metric, _, fmt in metrics:
                for source in sources:
                    value = card["metrics"][source][metric]
                    cells.append(f"{'-' if value is None else fmt.format(value):>22}")
            lines.append(f"{label:<8}{card['player_weeks']:>7}  " + "  ".join(cells))
        lines.append("")
    return "\n".join(lines)
