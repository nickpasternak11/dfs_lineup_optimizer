from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PlayerBio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gsis_id: str
    player: str
    position: str | None
    birthdate: date | None
    height: int | None = Field(description="Inches")
    weight: int | None = Field(description="Pounds")
    college: str | None
    draft_year: int | None
    draft_round: int | None
    draft_pick: int | None = Field(description="Overall pick number")


class _GameFields(BaseModel):
    """What every game log row has, player or defense.

    Team codes are nflverse's (LA for the Rams). proj_fpts and salary come
    from our player pool and are null for weeks it doesn't cover.
    """

    model_config = ConfigDict(extra="forbid")

    year: int
    week: int
    season_type: str = Field(description="REG or POST")
    team: str
    opponent: str | None
    home: bool | None
    team_score: int | None
    opponent_score: int | None
    dk_points: float
    proj_fpts: float | None
    salary: int | None


class PlayerGame(_GameFields):
    completions: int
    attempts: int
    passing_yards: int
    passing_tds: int
    interceptions: int
    carries: int
    rushing_yards: int
    rushing_tds: int
    targets: int
    receptions: int
    receiving_yards: int
    receiving_tds: int
    fumbles_lost: int


class DstGame(_GameFields):
    sacks: float
    interceptions: int
    fumble_recoveries: int
    defensive_tds: int
    return_tds: int
    safeties: int
    blocked_kicks: int
    points_allowed: int | None


class PlayerGameLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player: PlayerBio | None
    games: list[PlayerGame] = Field(description="Every game since 2018, oldest first")


class DstGameLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team: str
    games: list[DstGame] = Field(description="Every game since 2018, oldest first")
