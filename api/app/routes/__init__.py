from app.routes.optimize import router as optimize_router
from app.routes.projections import router as projections_router
from fastapi import APIRouter

# Every route declares a response_model, so FastAPI serializes through
# Pydantic straight to JSON bytes; no custom response class needed.
api_router = APIRouter()
api_router.include_router(optimize_router, prefix="/optimize")
api_router.include_router(projections_router, prefix="/projections")
