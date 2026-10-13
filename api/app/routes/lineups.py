from fastapi import Query

from app.helpers.api_router import APIRouter
from app.helpers.lineups import build_review
from app.models.responses.lineups import LineupReviewResponse

router = APIRouter()


@router.get(
    "/review",
    summary="Review saved lineups",
    response_model=LineupReviewResponse,
    description="The lineups saved before a week's games, how they scored, and "
    "the best lineup possible in hindsight. Defaults to the latest saved week.",
)
def get_lineup_review(
    year: int | None = Query(None, description="With week; the latest saved week when omitted"),
    week: int | None = Query(None, ge=1, le=22),
):
    return build_review(year, week)
