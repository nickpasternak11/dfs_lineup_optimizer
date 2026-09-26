from fastapi import HTTPException, status

from app.db.optimize import DFSLineupOptimizer
from app.helpers.api_router import APIRouter
from app.models.requests.optimize import OptimizeRequest
from app.models.responses.optimize import OptimizeResponse

router = APIRouter()


@router.post(
    "/",
    summary="Get optimized lineups",
    response_model=OptimizeResponse,
    description="Endpoint for getting optimized DFS lineups with parameters.",
)
def optimize(data: OptimizeRequest):
    # get optimal lineups
    try:
        optimizer = DFSLineupOptimizer(year=data.year, week=data.week)
        stack_qb_count = data.stack_qb_count or (1 if data.stack_qb else 0)
        if lineups := optimizer.get_optimal_lineups(
            stack_qb_count=stack_qb_count,
            avoid_te_flex=data.avoid_te_flex,
            include_started_players=data.include_started_players,
            excluded_players=data.excluded_players,
            included_players=data.included_players,
        ):
            return lineups
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
