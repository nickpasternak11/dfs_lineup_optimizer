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
    gsis_id: str | None = Field(
        description="nflverse player id, for /game-logs/players/{gsis_id}; NULL "
        "for DSTs and players who couldn't be linked"
    )
    actual_dk_points: float | None = Field(
        description="DraftKings points actually scored that week; NULL until "
        "the game is final, or if the player had no stats"
    )
    opp_fpts_allowed: float | None = Field(
        description="FPTS the opponent allowed to this position per game over "
        "the four weeks before the slate (all of last season in week 1); for a "
        "DST, what the opposing offense gave up to defenses"
    )
    opp_fpts_allowed_rank: int | None = Field(
        description="The opponent's rank by opp_fpts_allowed among the 32 "
        "teams: 1 allowed the fewest (toughest matchup), 32 the most"
    )
    opp_games: int | None = Field(description="Games behind opp_fpts_allowed")
    game_total: float | None = Field(description="The game's over/under")
    team_spread: float | None = Field(
        description="The team's point spread, betting-style: -3.5 when favored "
        "by 3.5"
    )
    implied_total: float | None = Field(
        description="The team's implied points, (game_total - team_spread) / 2; "
        "NULL until the game has lines"
    )
    model_fpts: float | None = Field(
        description="Our model's latest projection made before the player's "
        "kickoff; NULL until the model has projected the week"
    )


GetProjectionsResponse = list[ProjectionRecord]
