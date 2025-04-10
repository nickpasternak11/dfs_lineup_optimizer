from app.configs.configs import log
from app.db.optimize import DFSLineupOptimizer
from app.helpers.api_router import APIRouter
from app.models.responses.projections import GetProjectionsResponse
from app.models.requests.projections import GetProjectionsRequest
from fastapi import HTTPException, status

router = APIRouter()


@router.post(
    "/",
    summary="Get projections",
    response_model=GetProjectionsResponse,
    description="Endpoint for getting weekly projections.",
)
async def get_projections(data: GetProjectionsRequest):
    log.info(data)
    optimizer = DFSLineupOptimizer(week=data.week)
    try:
        df = optimizer.get_projections_df(use_stored_data=True)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
