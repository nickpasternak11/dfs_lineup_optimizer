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
    log.debug("request=%s", data)
    optimizer = DFSLineupOptimizer()
    lineups = []
    for weights in [(1, 0), (0.9, 0.1), (0.8, 0.2)]:
        try:
            lineup = optimizer.get_lineup_df(
                week=data.week if data.week else optimizer.current_week,
                dst=data.dst,
                one_te=data.one_te,
                use_avg_fpts=True if weights[1] > 0 else False,
                weights={"proj_fpts": weights[0], "avg_fpts": weights[1]},
                exclude_players=data.excluded_players,
                include_players=data.included_players,
                use_stored_data=True,
            )
            lineups.append(lineup.to_dict(orient="records"))
            log.debug("lineup=%s", lineup)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return lineups
