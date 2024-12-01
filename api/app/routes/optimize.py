from datetime import datetime
from app.configs.configs import log
from app.db.optimize import DFSLineupOptimizer, get_current_week
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
    # get year and week data
    year = datetime.now().year
    week = get_current_week(year=year) if data.week is None else data.week
    log.info("year=%s, week=%s", year, week)
    # get optimizer class object
    optimizer = DFSLineupOptimizer(year=year, week=week)
    lineups = []
    for weights in [(1, 0), (0.9, 0.1), (0.8, 0.2)]:
        log.info("weights=%s", weights)
        try:
            lineup = optimizer.get_lineup_df(
                dst=data.dst,
                one_te=data.one_te,
                use_avg_fpts=True if weights[1] > 0 else False,
                weights={"proj_fpts": weights[0], "avg_fpts": weights[1]},
                exclude_players=data.excluded_players,
                include_players=data.included_players,
                use_stored_data=True,
            )
            lineups.append(lineup.to_dict(orient="records"))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return lineups
