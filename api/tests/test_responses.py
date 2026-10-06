import re

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from app.application import application
from app.db.optimize import FLOAT_COLUMNS, PLAYER_POOL_QUERY, DFSLineupOptimizer
from app.helpers.optimize import dataframe_to_records
from app.models.responses.optimize import LineupPlayer, OptimizeResponse
from app.models.responses.projections import GetProjectionsResponse, ProjectionRecord


def query_columns() -> list[str]:
    # The main SELECT, not a CTE's: the one listing the most columns.
    select = max(
        re.findall(r"SELECT(.*?)\bFROM\b", PLAYER_POOL_QUERY.text, re.S),
        key=lambda s: s.count(","),
    )
    # "pool.year" -> "year"; "COALESCE(...) AS avg_fpts" -> "avg_fpts"
    return [
        (column.rsplit(" AS ", 1)[1] if " AS " in column else column.split(".")[-1]).strip()
        for column in re.sub(r"\([^)]*\)", "()", select).split(",")
    ]


@pytest.fixture
def full_pool(pool) -> pd.DataFrame:
    """The shared pool with every column the view returns, typed as read_sql
    gives them. The first player looks like a current week; the rest look like
    a week scraped before kickoff, home and salary_change were collected."""
    df = pool.copy()
    df["year"] = 2025
    df["week"] = 3
    df["opponent"] = "Z"
    df["home"] = pd.Series([True] + [None] * (len(df) - 1), dtype=object)
    df["grade"] = "B+"
    df["rank"] = range(1, len(df) + 1)
    # salary_change is float64 once any value is NULL.
    df["salary_change"] = [300.0] + [float("nan")] * (len(df) - 1)
    df["value"] = (df["proj_fpts"] / (df["salary"] / 1000)).round(2)
    df["injury_status"] = ["Questionable"] + [None] * (len(df) - 1)
    df["injury_type"] = ["Knee"] + [None] * (len(df) - 1)
    # Integer ids come back as float64 once any is NULL.
    df["fp_player_id"] = [17298.0] + [float("nan")] * (len(df) - 1)
    df["gsis_id"] = ["00-0034857"] + [None] * (len(df) - 1)
    df["actual_dk_points"] = [31.4] + [float("nan")] * (len(df) - 1)
    # Ranks and game counts are float64 too once a team has no recent games.
    df["opp_fpts_allowed"] = [27.3] + [float("nan")] * (len(df) - 1)
    df["opp_fpts_allowed_rank"] = [24.0] + [float("nan")] * (len(df) - 1)
    df["opp_games"] = [3.0] + [float("nan")] * (len(df) - 1)
    df.loc[0, "kickoff"] = pd.Timestamp("2099-09-27T17:00:00", tz="UTC")
    df.loc[1, "avg_fpts"] = float("nan")
    for column in FLOAT_COLUMNS:
        df[column] = df[column].astype(float)
    return df[query_columns()]


def test_models_cover_exactly_the_queried_columns():
    # extra="forbid" turns a missing field into a 500, so the two must agree.
    assert list(ProjectionRecord.model_fields) == query_columns()
    assert list(LineupPlayer.model_fields) == query_columns()


def test_projection_records_validate(full_pool):
    records = TypeAdapter(GetProjectionsResponse).validate_python(
        dataframe_to_records(full_pool)
    )

    current, historical = records[0], records[1]
    assert current.kickoff == "2099-09-27T17:00:00+0000"
    assert current.home is True
    assert current.salary_change == 300
    assert current.fp_player_id == 17298
    assert historical.fp_player_id is None
    assert (current.gsis_id, current.actual_dk_points) == ("00-0034857", 31.4)
    assert historical.gsis_id is None and historical.actual_dk_points is None
    assert (current.opp_fpts_allowed, current.opp_fpts_allowed_rank, current.opp_games) == (27.3, 24, 3)
    assert historical.opp_fpts_allowed_rank is None
    assert historical.kickoff is None
    assert historical.home is None
    assert historical.avg_fpts is None
    assert historical.salary_change is None
    assert historical.injury_status is None


def test_optimizer_lineups_validate(full_pool, make_optimizer):
    lineups = make_optimizer(full_pool).get_optimal_lineups()

    validated = TypeAdapter(OptimizeResponse).validate_python(lineups)

    assert len(validated) == 3
    assert all(len(lineup) == 9 for lineup in validated)


def test_unknown_columns_are_rejected(full_pool):
    record = dataframe_to_records(full_pool)[0] | {"surprise": 1}
    with pytest.raises(ValidationError):
        ProjectionRecord.model_validate(record)


@pytest.fixture
def client(full_pool, monkeypatch):
    monkeypatch.setattr(
        DFSLineupOptimizer, "get_projections_df", lambda self: full_pool
    )
    return TestClient(application)


def test_projections_json_keeps_its_format(client):
    response = client.post("/projections", json={"year": 2025, "week": 3})

    assert response.status_code == 200
    current, historical = response.json()[0:2]
    assert list(current) == query_columns()
    assert current["kickoff"] == "2099-09-27T17:00:00+0000"
    assert current["salary_change"] == 300
    assert historical["kickoff"] is None
    assert historical["home"] is None
    assert historical["avg_fpts"] is None
    assert historical["salary_change"] is None


def test_optimize_json_is_three_lineups_of_players(client):
    response = client.post(
        "/optimize", json={"year": 2025, "week": 3, "include_started_players": True}
    )

    assert response.status_code == 200
    lineups = response.json()
    assert len(lineups) == 3
    for lineup in lineups:
        assert len(lineup) == 9
        assert all(list(player) == query_columns() for player in lineup)


def response_schema(path: str) -> dict:
    operation = application.openapi()["paths"][path]["post"]
    return operation["responses"]["200"]["content"]["application/json"]["schema"]


def test_openapi_names_the_response_models():
    schemas = application.openapi()["components"]["schemas"]
    assert set(schemas["ProjectionRecord"]["properties"]) == set(query_columns())
    assert set(schemas["LineupPlayer"]["properties"]) == set(query_columns())

    projections = response_schema("/projections")
    assert projections["type"] == "array"
    assert projections["items"]["$ref"] == "#/components/schemas/ProjectionRecord"

    optimize = response_schema("/optimize")
    assert optimize["items"]["type"] == "array"
    assert optimize["items"]["items"]["$ref"] == "#/components/schemas/LineupPlayer"
