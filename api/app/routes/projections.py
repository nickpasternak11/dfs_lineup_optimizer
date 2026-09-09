from fastapi import HTTPException, status

from app.db.optimize import DFSLineupOptimizer
from app.helpers.api_router import APIRouter
from app.models.requests.projections import GetProjectionsRequest
from app.models.responses.projections import GetProjectionsResponse

router = APIRouter()


@router.get(
    "/current_year",
    summary="Get current year",
    response_model=int,
    description="Endpoint for getting the current projection year.",
)
async def get_current_year():
    return DFSLineupOptimizer().current_year


@router.get(
    "/current_week",
    summary="Get current week",
    response_model=int,
    description="Endpoint for getting the current projection week.",
)
async def get_current_week():
    return DFSLineupOptimizer().current_week


@router.post(
    "/",
    summary="Get projections",
    response_model=GetProjectionsResponse,
    description="Endpoint for getting weekly projections.",
)
async def get_projections(data: GetProjectionsRequest):
    optimizer = DFSLineupOptimizer(year=data.year, week=data.week)
    try:
        df = optimizer.get_projections_df(use_stored_data=True)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
