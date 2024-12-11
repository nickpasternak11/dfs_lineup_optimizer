from app.configs.configs import log
from app.db.optimize import DFSLineupOptimizer
from app.helpers.api_router import APIRouter
from app.models.requests.optimize import OptimizeRequest
from app.models.responses.optimize import OptimizeResponse
from fastapi import HTTPException, status

router = APIRouter()


@router.post(
    "/",
    summary="Get optimized lineups",
    response_model=OptimizeResponse,
    description="Endpoint for getting optimized DFS lineups with parameters.",
)
async def optimize(data: OptimizeRequest):
    log.info(data)
    # get optimal lineups
    optimizer = DFSLineupOptimizer(week=data.week)
    if lineups := optimizer.get_optimal_lineups(
        dst=data.dst,
        one_te=data.one_te,
        excluded_players=data.excluded_players,
        included_players=data.included_players,
        use_stored_data=True,
    ):
        return lineups
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
