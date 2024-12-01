from app.routes.optimize import router as optimize_router
from app.routes.projections import router as projections_router
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

api_router = APIRouter(default_response_class=ORJSONResponse)
api_router.include_router(optimize_router, prefix="/optimize")
api_router.include_router(projections_router, prefix="/projections")
