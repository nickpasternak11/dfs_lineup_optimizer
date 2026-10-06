"""Point-in-time features for projecting one game's DraftKings points.

Every history feature is built from the player's (or team's, or defense's)
earlier games only: values are shifted one game back before averaging, so a
row never sees its own result. The betting lines are the game's own, which
are known before kickoff.
"""

import numpy as np
import pandas as pd

SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]

# Half-lives in games, not weeks, so a bye or an injury decays nothing.
SHORT_HALFLIFE = 3
LONG_HALFLIFE = 10
# A defense's points allowed to a position: its last this-many games.
DEFENSE_WINDOW = 6

USAGE = [
    "dk_points", "targets", "receptions", "carries", "attempts",
    "passing_yards", "rushing_yards", "receiving_yards", "tds",
]
SHARES = ["target_share", "carry_share", "attempt_share"]
TEAM_TOTALS = ["targets", "carries", "attempts", "dk_points"]
DST_STATS = ["dk_points", "sacks", "interceptions", "fumble_recoveries", "points_allowed"]

LINE_FEATURES = ["implied_total", "opp_implied_total", "spread", "game_total", "home"]


def _order(df: pd.DataFrame) -> pd.Series:
    return df.year * 100 + df.week


def _history(df: pd.DataFrame, key: str, columns: list[str], halflives: dict[str, int]) -> pd.DataFrame:
    """Exponentially weighted means of each column over `key`'s earlier games,
    one per half-life, named `{column}_{suffix}`. df must be sorted by key,
    then game order."""
    previous = df.groupby(key, sort=False)[columns].shift(1)
    previous[key] = df[key]
    out = {}
    for suffix, halflife in halflives.items():
        averaged = previous.groupby(key, sort=False)[columns].ewm(halflife=halflife).mean()
        averaged = averaged.reset_index(level=0, drop=True).reindex(df.index)
        for column in columns:
            out[f"{column}_{suffix}"] = averaged[column]
    return pd.DataFrame(out, index=df.index)


def team_lines(games: pd.DataFrame) -> pd.DataFrame:
    """One row per team per game: its implied points, the opponent's, its own
    betting-style spread (favorites negative), the total and home/away.
    nflverse's spread_line is the home team's expected margin."""
    home = pd.DataFrame({
        "game_id": games.game_id,
        "team": games.home_team,
        "implied_total": (games.total_line + games.spread_line) / 2,
        "opp_implied_total": (games.total_line - games.spread_line) / 2,
        "spread": -games.spread_line,
        "game_total": games.total_line,
        "home": 1.0,
    })
    away = pd.DataFrame({
        "game_id": games.game_id,
        "team": games.away_team,
        "implied_total": (games.total_line - games.spread_line) / 2,
        "opp_implied_total": (games.total_line + games.spread_line) / 2,
        "spread": games.spread_line,
        "game_total": games.total_line,
        "home": 0.0,
    })
    return pd.concat([home, away], ignore_index=True)


def player_features(logs: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per QB/RB/WR/TE regular-season game, with its features and its
    DraftKings points (the target)."""
    df = logs[logs.season_type == "REG"].copy()
    df["position"] = df.position.replace({"FB": "RB"})
    df = df[df.position.isin(SKILL_POSITIONS)]
    df["tds"] = df.passing_tds + df.rushing_tds + df.receiving_tds
    df["t"] = _order(df)

    # The team's totals in each game, for each player's share of them.
    team = df.groupby(["year", "week", "team"])[TEAM_TOTALS].sum().add_prefix("team_")
    df = df.join(team, on=["year", "week", "team"])
    df["target_share"] = df.targets / df.team_targets.replace(0, np.nan)
    df["carry_share"] = df.carries / df.team_carries.replace(0, np.nan)
    df["attempt_share"] = df.attempts / df.team_attempts.replace(0, np.nan)

    df = df.sort_values(["gsis_id", "t"]).reset_index(drop=True)
    by_player = df.groupby("gsis_id", sort=False)
    df["prior_games"] = by_player.cumcount()
    df["season_games"] = df.groupby(["gsis_id", "year"], sort=False).cumcount()
    previous_year = by_player.year.shift(1)
    previous_week = by_player.week.shift(1)
    # Weeks since the last game; a new season counts as a long gap.
    df["weeks_off"] = (df.year - previous_year) * 18 + (df.week - previous_week)
    history = _history(df, "gsis_id", USAGE + SHARES, {"short": SHORT_HALFLIFE, "long": LONG_HALFLIFE})

    # The team's own recent offense.
    team = team.reset_index()
    team["t"] = _order(team)
    team = team.sort_values(["team", "t"]).reset_index(drop=True)
    team_columns = [f"team_{c}" for c in TEAM_TOTALS]
    team_history = _history(team, "team", team_columns, {"recent": SHORT_HALFLIFE})
    team = pd.concat([team[["year", "week", "team"]], team_history], axis=1)

    # What the opponent allowed to this position over its last few games.
    allowed = (
        df.groupby(["year", "week", "opponent", "position"]).dk_points.sum().rename("allowed").reset_index()
    )
    allowed["t"] = _order(allowed)
    allowed = allowed.sort_values(["opponent", "position", "t"])
    allowed["opp_allowed"] = allowed.groupby(["opponent", "position"]).allowed.transform(
        lambda s: s.shift(1).rolling(DEFENSE_WINDOW, min_periods=1).mean()
    )

    out = pd.concat([df, history], axis=1)
    out = out.merge(team, on=["year", "week", "team"], how="left")
    out = out.merge(
        allowed[["year", "week", "opponent", "position", "opp_allowed"]],
        on=["year", "week", "opponent", "position"],
        how="left",
    )
    out = out.merge(team_lines(games), on=["game_id", "team"], how="left")
    return out


def dst_features(dst: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per team defense per regular-season game."""
    df = dst[dst.season_type == "REG"].copy()
    df["position"] = "DST"
    df["t"] = _order(df)
    df = df.sort_values(["team", "t"]).reset_index(drop=True)
    history = _history(df, "team", DST_STATS, {"short": SHORT_HALFLIFE, "long": LONG_HALFLIFE})

    # What the offense this defense faces gave up to the defenses it played.
    given_up = df[["year", "week", "opponent", "t", "dk_points"]].sort_values(["opponent", "t"])
    given_up["opp_allowed"] = given_up.groupby("opponent").dk_points.transform(
        lambda s: s.shift(1).rolling(DEFENSE_WINDOW, min_periods=1).mean()
    )

    out = pd.concat([df, history], axis=1)
    out = out.merge(given_up[["year", "week", "opponent", "opp_allowed"]], on=["year", "week", "opponent"], how="left")
    out = out.merge(team_lines(games), on=["game_id", "team"], how="left")
    return out


PLAYER_FEATURES = (
    ["prior_games", "season_games", "weeks_off"]
    + [f"{c}_{s}" for c in USAGE + SHARES for s in ("short", "long")]
    + [f"team_{c}_recent" for c in TEAM_TOTALS]
    + ["opp_allowed"]
    + LINE_FEATURES
)
DST_FEATURES = [f"{c}_{s}" for c in DST_STATS for s in ("short", "long")] + ["opp_allowed"] + LINE_FEATURES


def feature_columns(position: str) -> list[str]:
    return DST_FEATURES if position == "DST" else PLAYER_FEATURES
