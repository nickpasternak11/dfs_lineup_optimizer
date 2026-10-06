from app.routes.accuracy import router as accuracy_router
from app.routes.game_logs import router as game_logs_router
from app.routes.optimize import router as optimize_router
from app.routes.projections import router as projections_router
from fastapi import APIRouter

# Every route declares a response_model, so FastAPI serializes through
# Pydantic straight to JSON bytes; no custom response class needed.
api_router = APIRouter()
api_router.include_router(optimize_router, prefix="/optimize")
api_router.include_router(projections_router, prefix="/projections")
api_router.include_router(game_logs_router, prefix="/game-logs")
api_router.include_router(accuracy_router, prefix="/accuracy")
