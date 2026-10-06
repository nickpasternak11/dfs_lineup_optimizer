from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WeekRef(_Model):
    year: int
    week: int


class ReviewPlayer(_Model):
    slot: int | None
    player: str
    position: str
    team: str | None
    salary: int
    projection: float | None = Field(description="The lineup's source's own projection; none for the best lineup")
    actual: float | None = Field(description="DraftKings points scored; NULL if the player didn't play or the game isn't final")


class ReviewLineup(_Model):
    source: str = Field(description="fantasypros or model")
    strategy: str = Field(description="projection, blend_90_10 or blend_80_20")
    projected: float
    actual: float = Field(description="Points scored, a player who didn't play counting zero")
    players: list[ReviewPlayer]


class BestLineup(_Model):
    actual: float
    players: list[ReviewPlayer]


class LineupTotals(_Model):
    source: str
    strategy: str
    projected: float
    actual: float


class WeekTotals(_Model):
    week: int
    complete: bool = Field(description="Every game the lineups could use is final")
    best: float | None = Field(description="NULL until the week has results")
    lineups: list[LineupTotals]


class LineupReviewResponse(_Model):
    weeks: list[WeekRef] = Field(description="Weeks with saved lineups, newest first")
    year: int | None
    week: int | None
    saved_at: datetime | None = Field(description="When the reviewed lineups were saved")
    complete: bool = Field(description="Every game the lineups could use is final")
    lineups: list[ReviewLineup]
    best: BestLineup | None = Field(description="The best lineup in hindsight from the same players")
    season: list[WeekTotals] = Field(description="Every saved week of the season, oldest first")
