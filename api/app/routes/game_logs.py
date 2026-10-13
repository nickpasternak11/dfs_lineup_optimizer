import pandas as pd
from fastapi import HTTPException, status

from app.db import game_logs
from app.helpers.api_router import APIRouter
from app.helpers.optimize import dataframe_to_records
from app.models.responses.game_logs import DstGameLogResponse, PlayerGameLogResponse

router = APIRouter()


def _bio_record(bio: dict) -> dict:
    # pandas hands back NaN/NaT for missing bio fields.
    return {key: (None if pd.isna(value) else value) for key, value in bio.items()}


@router.get(
    "/players/{gsis_id}",
    summary="Get a player's game log",
    response_model=PlayerGameLogResponse,
    description="Every game since 2018 with DraftKings points and key stats, "
    "plus the player's bio. gsis_id comes from the projections response.",
)
def get_player_game_log(gsis_id: str):
    bio, games = game_logs.load_player_game_log(gsis_id)
    if bio is None and games.empty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No player {gsis_id}")
    return {
        "player": None if bio is None else _bio_record(bio),
        "games": dataframe_to_records(games),
    }


@router.get(
    "/dst/{team}",
    summary="Get a team defense's game log",
    response_model=DstGameLogResponse,
    description="Every game since 2018 with DraftKings DST points and stats. "
    "Accepts either the salary page's or nflverse's team code (LAR or LA).",
)
def get_dst_game_log(team: str):
    games = game_logs.load_dst_game_log(team)
    if games.empty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No games for {team}")
    return {"team": team.upper(), "games": dataframe_to_records(games)}
