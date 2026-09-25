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
