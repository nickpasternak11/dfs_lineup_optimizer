import datetime
import re

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.application import application
from app.db import game_logs
from app.models.responses.game_logs import DstGame, PlayerBio, PlayerGame

client = TestClient(application)


def selected_columns(query) -> list[str]:
    """Output names of a SELECT: the alias after AS, else the bare column."""
    # The main SELECT, not a CTE's: the one listing more than four columns.
    select = next(s for s in re.findall(r"SELECT(.*?)\bFROM\b", query.text, re.S) if s.count(",") > 4)
    names = []
    for item in select.split(","):
        item = item.strip()
        names.append(item.rsplit(" AS ", 1)[1] if " AS " in item else item.split(".")[-1])
    return names


@pytest.mark.parametrize(
    "query, model",
    [
        (game_logs.PLAYER_BIO_QUERY, PlayerBio),
        (game_logs.PLAYER_GAMES_QUERY, PlayerGame),
        (game_logs.DST_GAMES_QUERY, DstGame),
    ],
)
def test_models_cover_exactly_the_queried_columns(query, model):
    # extra="forbid" turns a stray column into a 500, so the two must agree.
    assert sorted(selected_columns(query)) == sorted(model.model_fields)


def player_games(**overrides) -> pd.DataFrame:
    """Two games as read_sql returns them: the second predates our pool, so
    its projection and salary are missing."""
    df = pd.DataFrame(
        {
            "year": [2026, 2026], "week": [1, 2], "season_type": ["REG", "REG"],
            "team": ["BUF", "BUF"], "opponent": ["HOU", "NYJ"], "home": [True, False],
            "team_score": [27, 30], "opponent_score": [20, 10],
            "dk_points": [35.66, 18.4], "proj_fpts": [22.6, float("nan")],
            "salary": [7700.0, float("nan")],
            "completions": [25, 20], "attempts": [36, 30], "passing_yards": [334, 220],
            "passing_tds": [2, 1], "interceptions": [0, 1], "carries": [6, 4],
            "rushing_yards": [40, 12], "rushing_tds": [1, 0], "targets": [0, 0],
            "receptions": [0, 0], "receiving_yards": [0, 0], "receiving_tds": [0, 0],
            "fumbles_lost": [0, 0],
        }
    )
    return df.assign(**overrides)


BIO = {
    "gsis_id": "00-0034857", "player": "Josh Allen", "position": "QB",
    "birthdate": datetime.date(1996, 5, 21), "height": 77, "weight": 237,
    "college": "Wyoming", "draft_year": 2018, "draft_round": 1, "draft_pick": 7,
}


def test_player_game_log_returns_bio_and_games(monkeypatch):
    monkeypatch.setattr(game_logs, "load_player_game_log", lambda gsis_id: (BIO, player_games()))

    response = client.get("/game-logs/players/00-0034857")

    assert response.status_code == 200
    body = response.json()
    assert body["player"]["birthdate"] == "1996-05-21"
    assert body["player"]["draft_pick"] == 7
    first, second = body["games"]
    assert (first["week"], first["opponent"], first["home"], first["dk_points"]) == (1, "HOU", True, 35.66)
    assert (first["proj_fpts"], first["salary"]) == (22.6, 7700)
    # Weeks our pool doesn't cover have no projection or salary.
    assert second["proj_fpts"] is None and second["salary"] is None


def test_a_player_without_a_bio_still_gets_games(monkeypatch):
    monkeypatch.setattr(game_logs, "load_player_game_log", lambda gsis_id: (None, player_games()))
    body = client.get("/game-logs/players/00-0034857").json()
    assert body["player"] is None
    assert len(body["games"]) == 2


def test_missing_bio_fields_are_null(monkeypatch):
    bio = {**BIO, "birthdate": pd.NaT, "college": float("nan"), "draft_round": float("nan")}
    monkeypatch.setattr(game_logs, "load_player_game_log", lambda gsis_id: (bio, player_games()))
    player = client.get("/game-logs/players/00-0034857").json()["player"]
    assert (player["birthdate"], player["college"], player["draft_round"]) == (None, None, None)


def test_unknown_player_is_a_404(monkeypatch):
    monkeypatch.setattr(game_logs, "load_player_game_log", lambda gsis_id: (None, player_games().iloc[0:0]))
    assert client.get("/game-logs/players/00-9999999").status_code == 404


def test_dst_game_log(monkeypatch):
    requested = []

    def load(team):
        requested.append(team)
        return pd.DataFrame(
            {
                "year": [2025], "week": [5], "season_type": ["REG"], "team": ["JAX"],
                "opponent": ["KC"], "home": [True], "team_score": [31], "opponent_score": [28],
                "dk_points": [7.0], "proj_fpts": [float("nan")], "salary": [float("nan")],
                "sacks": [0.0], "interceptions": [1], "fumble_recoveries": [0],
                "defensive_tds": [1], "return_tds": [0], "safeties": [0], "blocked_kicks": [0],
                "points_allowed": [28],
            }
        )

    monkeypatch.setattr(game_logs, "load_dst_game_log", load)
    body = client.get("/game-logs/dst/jac").json()

    assert requested == ["jac"]  # the SQL maps JAC/JAX itself
    assert body["team"] == "JAC"
    (game,) = body["games"]
    assert (game["points_allowed"], game["defensive_tds"], game["dk_points"]) == (28, 1, 7.0)


def test_dst_without_games_is_a_404(monkeypatch):
    monkeypatch.setattr(game_logs, "load_dst_game_log", lambda team: pd.DataFrame())
    assert client.get("/game-logs/dst/XYZ").status_code == 404
