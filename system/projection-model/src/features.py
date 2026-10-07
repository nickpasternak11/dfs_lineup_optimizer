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
SHARES = ["target_share", "carry_share", "attempt_share", "snap_share"]
TEAM_TOTALS = ["targets", "carries", "attempts", "dk_points"]
# From the schedule (nflverse.schedule), for defenses only: for players it
# backtested no better than without. Only what's known before kickoff: the
# schedule fills in temperature and wind after a game, and a retractable
# roof's open or closed on the day.
GAME_CONTEXT = ["rest_days", "dome"]
DST_STATS = ["dk_points", "sacks", "interceptions", "fumble_recoveries", "points_allowed"]

LINE_FEATURES = ["implied_total", "opp_implied_total", "spread", "game_total", "home"]

# A player stays on a team's list of recent regulars for this many of its
# games after their last appearance.
VACATED_WINDOW = 3
# The role that makes a player a regular. The logs only list players who
# recorded a stat, so an active player with no touches looks absent; above
# these shares, no stats almost always means they didn't play.
REGULAR_SHARE = {"target_share": 0.08, "carry_share": 0.10, "attempt_share": 0.50}


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


def vacated_usage(df: pd.DataFrame, snaps: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The usage a team has to replace in each game: the recent shares of its
    regulars who aren't playing (injured, traded, gone since last season).
    Who's inactive is announced 90 minutes before kickoff, ahead of DraftKings'
    lineup lock, so this is pre-game information.

    df: player rows with shares and positions, sorted by player then game.
    snaps: snap counts, which say exactly who played (from 2013); without
    them, a player plays when the logs list them.
    Returns per team-game totals and per team-game-position totals, keyed by
    year, week, team (and position).
    """
    shares = list(REGULAR_SHARE)
    # Each player's role coming out of each game: the average including it.
    role = df.groupby("gsis_id", sort=False)[shares].ewm(halflife=SHORT_HALFLIFE).mean()
    role = role.reset_index(level=0, drop=True).reindex(df.index)

    games = df[["team", "year", "week", "t"]].drop_duplicates().sort_values(["team", "t"])
    games["g"] = games.groupby("team").cumcount()
    rows = pd.concat([df[["gsis_id", "team", "position", "t"]], role], axis=1)
    rows = rows.merge(games[["team", "t", "g"]], on=["team", "t"])

    # Every regular is expected in the team's next few games...
    expected = pd.concat([rows.assign(g=rows.g + k) for k in range(1, VACATED_WINDOW + 1)])
    expected = expected.sort_values("t").drop_duplicates(["team", "g", "gsis_id"], keep="last")
    # ...and counts as vacated in the ones they don't play.
    keys = games[["team", "g", "year", "week"]]
    played = df[["year", "week", "gsis_id"]]
    if snaps is not None:
        played = pd.concat([played, snaps.loc[snaps.offense_snaps > 0, ["year", "week", "gsis_id"]]])
    played = played.drop_duplicates().assign(played=True)
    expected = expected.drop(columns="t").merge(keys, on=["team", "g"])
    absent = expected.merge(played, on=["year", "week", "gsis_id"], how="left")
    absent = absent[absent.played.isna()].copy()
    for share, floor in REGULAR_SHARE.items():
        absent[share] = absent[share].where(absent[share] >= floor, 0.0)

    team = absent.groupby(["team", "g"])[shares].sum().add_prefix("vacated_").reset_index()
    team = team.merge(keys, on=["team", "g"]).drop(columns="g")
    position = (
        absent.groupby(["team", "g", "position"])[["target_share", "carry_share"]]
        .sum()
        .add_prefix("vacated_position_")
        .reset_index()
        .merge(keys, on=["team", "g"])
        .drop(columns="g")
    )
    return team, position


def game_context(schedule: pd.DataFrame) -> pd.DataFrame:
    """One row per team per game: days of rest, and whether it's in a fixed
    dome."""
    rest = pd.concat(
        [
            pd.DataFrame({
                "game_id": schedule.game_id,
                "team": schedule[f"{side}_team"],
                "rest_days": schedule[f"{side}_rest"],
            })
            for side in ("home", "away")
        ],
        ignore_index=True,
    )
    dome = pd.DataFrame({"game_id": schedule.game_id, "dome": (schedule.roof == "dome").astype(float)})
    return rest.merge(dome, on="game_id")


def _with_context(out: pd.DataFrame, schedule: pd.DataFrame | None) -> pd.DataFrame:
    if schedule is None:
        return out.assign(**dict.fromkeys(GAME_CONTEXT, np.nan))
    return out.merge(game_context(schedule), on=["game_id", "team"], how="left")


def player_features(logs: pd.DataFrame, games: pd.DataFrame, snaps: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per QB/RB/WR/TE regular-season game, with its features and its
    DraftKings points (the target). `snaps` (nflverse.snap_counts) adds each
    game's share of the offense's snaps and says exactly who played (from
    2013); without it those features are missing, which the model handles."""
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
    if snaps is None:
        df["snap_share"] = np.nan
    else:
        snap_share = snaps.drop_duplicates(["year", "week", "gsis_id"])[["year", "week", "gsis_id", "snap_share"]]
        df = df.merge(snap_share, on=["year", "week", "gsis_id"], how="left")

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

    vacated_team, vacated_position = vacated_usage(df, snaps)
    out = out.merge(vacated_team, on=["year", "week", "team"], how="left")
    out = out.merge(vacated_position, on=["year", "week", "team", "position"], how="left")
    out[VACATED_FEATURES] = out[VACATED_FEATURES].fillna(0.0)
    return out


def dst_features(dst: pd.DataFrame, games: pd.DataFrame, schedule: pd.DataFrame | None = None) -> pd.DataFrame:
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
    return _with_context(out, schedule)


VACATED_FEATURES = [
    "vacated_target_share", "vacated_carry_share", "vacated_attempt_share",
    "vacated_position_target_share", "vacated_position_carry_share",
]

PLAYER_FEATURES = (
    ["prior_games", "season_games", "weeks_off"]
    + [f"{c}_{s}" for c in USAGE + SHARES for s in ("short", "long")]
    + [f"team_{c}_recent" for c in TEAM_TOTALS]
    + ["opp_allowed"]
    + LINE_FEATURES
    + VACATED_FEATURES
)
DST_FEATURES = (
    [f"{c}_{s}" for c in DST_STATS for s in ("short", "long")] + ["opp_allowed"] + LINE_FEATURES + GAME_CONTEXT
)


def feature_columns(position: str) -> list[str]:
    return DST_FEATURES if position == "DST" else PLAYER_FEATURES
