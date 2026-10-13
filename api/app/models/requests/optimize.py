from typing import Literal

from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    year: int | None = None
    week: int | None = None
    stack_qb: bool = False
    stack_qb_count: int = Field(default=0, ge=0, le=2)
    avoid_te_flex: bool = False
    include_started_players: bool = False
    excluded_players: list[str] = []
    included_players: list[str] = []
    projection_source: Literal["fantasypros", "model"] = Field(
        default="fantasypros",
        description="Optimize on FantasyPros' projection or our model's latest one before kickoff",
    )
