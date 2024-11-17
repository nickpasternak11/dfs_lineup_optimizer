from app.routes.optimize import router as optimize_router
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

api_router = APIRouter(default_response_class=ORJSONResponse)
api_router.include_router(optimize_router, prefix="/optimize", tags=["Optimizer"])
