from typing import List, Optional

from pydantic import BaseModel


class OptimizeRequest(BaseModel):
    year: Optional[int] = None
    week: Optional[int] = None
    dst: Optional[str] = None
    one_te: Optional[bool] = False
    excluded_players: List[str] = []
    included_players: List[str] = []
