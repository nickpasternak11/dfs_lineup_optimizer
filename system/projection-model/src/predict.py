"""This week's projections, made before kickoff and stored as a snapshot.

The model trains on every game played so far and predicts each pool player
whose game hasn't started. A placeholder game-log row stands in for each
upcoming game, so the same feature code builds its history from earlier
games and its betting lines from the schedule; its own stats are unknown.
"""

from datetime import datetime

import numpy as np
import pandas as pd
from dfs_db import ModelProjection, session_scope, upsert_dataframe

from src.configs import MODEL_VERSION, POSITIONS, log
from src.features import dst_features, player_features
from src.model import train_and_predict

# Players the crosswalk doesn't link (mostly rookies) still get a row, keyed
# by name; with no history, the model projects them from their game's lines.
UNLINKED_PREFIX = "pool:"


def upcoming_games(games: pd.DataFrame, year: int, week: int, now: datetime) -> pd.DataFrame:
    """One row per team with a game this week that hasn't kicked off."""
    week_games = games[(games.year == year) & (games.week == week) & (games.kickoff > now)]
    sides = []
    for team, opponent in (("home_team", "away_team"), ("away_team", "home_team")):
        sides.append(week_games[["game_id", "kickoff", team, opponent]].rename(columns={team: "team", opponent: "opponent"}))
    return pd.concat(sides, ignore_index=True)


def placeholder_rows(pool: pd.DataFrame, upcoming: pd.DataFrame, year: int, week: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Game-log rows (players, defenses) for pool players whose game is still
    to come, with their stats unknown. `pool_player` keeps the pool's name."""
    rows = pool.merge(upcoming[["team", "opponent", "game_id"]], on="team")
    rows = rows.assign(year=year, week=week, season_type="REG", dk_points=np.nan, pool_player=rows.player)
    players = rows[rows.position != "DST"].copy()
    players["gsis_id"] = players.gsis_id.fillna(UNLINKED_PREFIX + players.player)
    players = players.drop_duplicates("gsis_id")
    defenses = rows[rows.position == "DST"].drop(columns=["gsis_id", "player"]).drop_duplicates("team")
    return players, defenses


def predict_week(
    tables: dict,
    pool: pd.DataFrame,
    year: int,
    week: int,
    now: datetime,
    snaps: pd.DataFrame | None = None,
    schedule: pd.DataFrame | None = None,
    model_factory=None,
) -> pd.DataFrame:
    """model_projections rows for every pool player whose game is still to
    come (none once the week's games have all kicked off)."""
    upcoming = upcoming_games(tables["games"], year, week, now)
    players, defenses = placeholder_rows(pool, upcoming, year, week)
    if players.empty and defenses.empty:
        return pd.DataFrame(columns=[c.name for c in ModelProjection.__table__.columns])

    features = pd.concat(
        [
            player_features(pd.concat([tables["player_logs"], players], ignore_index=True), tables["games"], snaps),
            dst_features(pd.concat([tables["dst_logs"], defenses], ignore_index=True), tables["games"], schedule),
        ],
        ignore_index=True,
    )
    is_upcoming = features.pool_player.notna()
    kwargs = {} if model_factory is None else {"model_factory": model_factory}
    predicted = train_and_predict(features[~is_upcoming], features[is_upcoming], POSITIONS, **kwargs)

    teams = pool.drop_duplicates("player").set_index("player").pool_team
    gsis_id = predicted.gsis_id.where(~predicted.gsis_id.fillna("").str.startswith(UNLINKED_PREFIX))
    return pd.DataFrame({
        "year": year,
        "week": week,
        "player": predicted.pool_player,
        "generated_at": now,
        "position": predicted.position,
        "team": predicted.pool_player.map(teams),
        "gsis_id": gsis_id.where(predicted.position != "DST"),
        "proj_dk_points": predicted.model.round(2),
        "model_version": MODEL_VERSION,
    })


def store(projections: pd.DataFrame) -> int:
    with session_scope() as session:
        written = upsert_dataframe(session, ModelProjection, projections)
    log.info("Stored %s projections", written)
    return written
