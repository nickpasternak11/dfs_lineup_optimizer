from pydantic import BaseModel


class OptimizeRequest(BaseModel):
    year: int | None = None
    week: int | None = None
    stack_qb: bool = False
    excluded_players: list[str] = []
    included_players: list[str] = []
