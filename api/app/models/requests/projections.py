from pydantic import BaseModel


class GetProjectionsRequest(BaseModel):
    year: int | None = None
    week: int | None = None
