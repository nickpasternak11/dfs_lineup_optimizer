from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from optimizer import DFSLineupOptimizer
from pydantic import BaseModel

app = FastAPI(title="DFSLineupOptimizer", redoc_url=None, docs_url=None)

# Add CORSMiddleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class OptimizeRequest(BaseModel):
    week: Optional[int] = None
    dst: Optional[str] = None
    one_te: Optional[bool] = False
    excludedPlayers: List[str] = []
    includedPlayers: List[str] = []


@app.post("/optimize")
async def optimize(request: OptimizeRequest):
    optimizer = DFSLineupOptimizer()

    lineups = []
    for weights in [(1, 0), (0.9, 0.1), (0.8, 0.2)]:
        try:
            lineup = optimizer.get_lineup_df(
                week=request.week if request.week else optimizer.current_week,
                dst=request.dst,
                one_te=request.one_te,
                use_avg_fpts=True if weights[1] > 0 else False,
                weights={"proj_fpts": weights[0], "avg_fpts": weights[1]},
                exclude_players=request.excludedPlayers,
                include_players=request.includedPlayers,
                use_stored_data=True,
            )
            lineups.append(lineup.to_dict(orient="records"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return lineups
