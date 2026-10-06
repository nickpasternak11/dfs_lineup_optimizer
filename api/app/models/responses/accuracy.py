from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceInfo(_Model):
    key: str
    label: str
    description: str


class Metrics(_Model):
    mae: float | None = Field(description="Average absolute miss, in FPTS")
    bias: float | None = Field(description="Average of actual minus projected; positive when players beat it")
    rmse: float | None
    within: float | None = Field(description="Share of projections within 5 FPTS of the actual")
    rank_corr: float | None = Field(
        description="Spearman correlation with the actual inside each position-week, "
        "averaged by player count; NULL for slices that cut across position-weeks"
    )


class Cell(_Model):
    player_weeks: int
    metrics: dict[str, Metrics] = Field(description="Keyed by source")


class PositionCell(Cell):
    position: str


class WeekCell(Cell):
    year: int
    week: int


class SalaryCell(Cell):
    low: int | None
    high: int | None


class CalibrationBin(_Model):
    low: float | None
    high: float | None
    player_weeks: int
    predicted: float
    actual: float


class Coverage(_Model):
    considered: int = Field(description="Player-weeks projected for min_proj or more by any source, with a final game")
    scored: int = Field(description="Of those, with actual DraftKings points")
    no_stats: int = Field(description="Matched to nflverse but without stats that week (inactive)")
    unlinked: int = Field(description="Not matched to nflverse")
    no_baseline: int = Field(description="Scored, but some source had no projection (e.g. no recent games)")
    evaluated: int = Field(description="Compared: every source and the actual present")


class AccuracyResponse(_Model):
    seasons: list[int]
    sources: list[SourceInfo]
    year: int | None
    position: str | None
    min_proj: float
    coverage: Coverage
    summary: Cell
    by_position: list[PositionCell]
    by_week: list[WeekCell]
    by_salary: list[SalaryCell]
    calibration: dict[str, list[CalibrationBin]]
