from pydantic import BaseModel, ConfigDict, Field


class ProjectionRecord(BaseModel):
    """One row of the weekly_player_pool view, as PLAYER_POOL_QUERY selects it.

    Extra keys are rejected rather than dropped, so a column added to the query
    without a matching field here fails loudly instead of vanishing from the
    response. Everything the view can leave NULL is optional: weeks scraped
    before a column existed (kickoff, home, salary_change, ...) carry None.
    """

    model_config = ConfigDict(extra="forbid")

    year: int
    week: int
    player: str
    position: str
    team: str | None
    # Kept as the string dataframe_to_records produces; a datetime field would
    # re-render the offset as "+00:00".
    kickoff: str | None = Field(
        description="Kickoff time as %Y-%m-%dT%H:%M:%S%z, e.g. 2026-10-04T20:05:00+0000"
    )
    opponent: str | None
    home: bool | None
    grade: str | None
    rank: int | None
    avg_fpts: float | None
    proj_fpts: float
    salary: int
    salary_change: int | None
    value: float | None = Field(description="proj_fpts per $1,000 of salary")
    injury_status: str | None
    injury_type: str | None
    fp_player_id: int | None = Field(
        description="FantasyPros player id, used for headshots; NULL for weeks "
        "scraped before it was collected"
    )


GetProjectionsResponse = list[ProjectionRecord]
