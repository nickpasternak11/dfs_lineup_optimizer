from typing import Optional

from pydantic import BaseModel


class GetProjectionsRequest(BaseModel):
    year: Optional[int] = None
    week: Optional[int] = None
