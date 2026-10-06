from typing import Literal

from fastapi import Query

from app.db import accuracy
from app.helpers.accuracy import build_report
from app.helpers.api_router import APIRouter
from app.models.responses.accuracy import AccuracyResponse

router = APIRouter()


@router.get(
    "/",
    summary="Get projection accuracy",
    response_model=AccuracyResponse,
    description="How each projection source compared with actual DraftKings "
    "points over every past week, on the same player-weeks.",
)
def get_accuracy(
    year: int | None = Query(None, description="One season; all when omitted"),
    position: Literal["QB", "RB", "WR", "TE", "DST"] | None = None,
    min_proj: float = Query(
        5.0, ge=0, le=40, description="Count a player when any source projected this many FPTS"
    ),
):
    return build_report(accuracy.load_rows(), year=year, position=position, min_proj=min_proj)
