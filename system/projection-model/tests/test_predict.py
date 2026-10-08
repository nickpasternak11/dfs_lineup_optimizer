from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from src import predict
from src.configs import MODEL_VERSION
from src.features import player_features

NOW = datetime(2025, 10, 12, 15, 0, tzinfo=timezone.utc)
STATS = [
    "attempts", "carries", "targets", "receptions", "passing_yards", "passing_tds", "interceptions",
    "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds", "fumbles_lost",
]


def log(week, gsis_id, position, team, opponent, points):
    row = dict.fromkeys(STATS, 1)
    row.update(
        year=2025, week=week, gsis_id=gsis_id, player=gsis_id, position=position, team=team,
        opponent=opponent, game_id=f"g{week}{team}", season_type="REG", dk_points=points,
    )
    return row


def dst(week, team, opponent, points):
    return {
        "year": 2025, "week": week, "team": team, "opponent": opponent, "game_id": f"g{week}{team}",
        "season_type": "REG", "sacks": 2.0, "interceptions": 1, "fumble_recoveries": 0,
        "points_allowed": 20, "dk_points": points,
    }


def game(week, home, away, kickoff):
    return {"game_id": f"g{week}{home}", "year": 2025, "week": week, "kickoff": kickoff,
            "home_team": home, "away_team": away, "spread_line": 3.0, "total_line": 44.0}


@pytest.fixture
def tables():
    played = datetime(2025, 9, 28, 17, 0, tzinfo=timezone.utc)
    logs = [log(w, "wr1", "WR", "BUF", "MIA", p) for w, p in [(3, 10.0), (4, 20.0)]]
    logs += [log(w, "qb1", "QB", "KC", "DEN", 22.0) for w in (3, 4)]
    games = [game(w, "BUF", "MIA", played) for w in (3, 4)] + [game(w, "KC", "DEN", played) for w in (3, 4)]
    # Week 5: Bills-Dolphins later today; Chiefs-Broncos kicked off Thursday.
    games += [game(5, "BUF", "MIA", datetime(2025, 10, 12, 17, 0, tzinfo=timezone.utc)),
              game(5, "KC", "DEN", datetime(2025, 10, 9, 0, 15, tzinfo=timezone.utc))]
    games = pd.DataFrame(games)
    games["kickoff"] = pd.to_datetime(games.kickoff, utc=True)
    dsts = [dst(w, "BUF", "MIA", 8.0) for w in (3, 4)] + [dst(w, "MIA", "BUF", 3.0) for w in (3, 4)]
    return {"player_logs": pd.DataFrame(logs), "dst_logs": pd.DataFrame(dsts), "games": games}


@pytest.fixture
def pool():
    # Pool team codes go through nfl_team() in the query, so they're nflverse's.
    return pd.DataFrame({
        "player": ["Receiver One", "Rookie Wideout", "Quarterback One", "Bills"],
        "position": ["WR", "WR", "QB", "DST"],
        "pool_team": ["BUF", "BUF", "KC", "BUF"],
        "team": ["BUF", "BUF", "KC", "BUF"],
        "gsis_id": ["wr1", None, "qb1", None],
    })


def test_only_games_still_to_come_are_projected(tables, pool):
    upcoming = predict.upcoming_games(tables["games"], 2025, 5, NOW)
    assert set(upcoming.team) == {"BUF", "MIA"}
    players, defenses = predict.placeholder_rows(pool, upcoming, 2025, 5)
    assert sorted(players.pool_player) == ["Receiver One", "Rookie Wideout"]  # the Chiefs already played
    assert list(defenses.pool_player) == ["Bills"]
    assert players.dk_points.isna().all()


def test_placeholders_get_their_history_from_earlier_games(tables, pool):
    upcoming = predict.upcoming_games(tables["games"], 2025, 5, NOW)
    players, _ = predict.placeholder_rows(pool, upcoming, 2025, 5)
    features = player_features(pd.concat([tables["player_logs"], players], ignore_index=True), tables["games"])
    wr1 = features[(features.gsis_id == "wr1") & (features.week == 5)].iloc[0]
    assert 10.0 < wr1.dk_points_short < 20.0  # weeks 3 and 4, weighted to 4
    assert (wr1.prior_games, wr1.implied_total) == (2, 23.5)
    # The rookie has no history; the lines still apply.
    rookie = features[features.gsis_id == "pool:Rookie Wideout"].iloc[0]
    assert rookie.prior_games == 0 and np.isnan(rookie.dk_points_short)


class Mean:
    """Stands in for the model: predicts the training rows' average."""

    def fit(self, X, y):
        self.mean = float(y.mean())
        return self

    def predict(self, X):
        return [self.mean] * len(X)


def test_a_snapshot_row_per_upcoming_pool_player(tables, pool):
    rows = predict.predict_week(tables, pool, 2025, 5, NOW, model_factory=Mean).set_index("player")

    assert sorted(rows.index) == ["Bills", "Receiver One", "Rookie Wideout"]
    assert rows.loc["Receiver One", "proj_dk_points"] == 15.0  # WR games: 10 and 20
    assert rows.loc["Bills", "proj_dk_points"] == 5.5  # DST games: 8, 8, 3, 3
    assert rows.loc["Receiver One", "gsis_id"] == "wr1"
    # Unlinked players and defenses store no gsis_id.
    assert pd.isna(rows.loc["Rookie Wideout", "gsis_id"]) and pd.isna(rows.loc["Bills", "gsis_id"])
    assert (rows.team == "BUF").all() and (rows.week == 5).all()
    assert (rows.generated_at == NOW).all() and (rows.model_version == MODEL_VERSION).all()


def test_nothing_to_project_once_every_game_has_started(tables, pool):
    later = datetime(2025, 10, 14, tzinfo=timezone.utc)
    assert predict.predict_week(tables, pool, 2025, 5, later, model_factory=Mean).empty


def test_players_ruled_out_are_projected_at_zero(tables, pool):
    tables = {**tables, "injuries": pd.DataFrame({
        "year": [2025], "week": [5], "gsis_id": ["wr1"], "team": ["BUF"],
        "report_status": ["Out"], "practice_status": ["DNP"],
    })}
    rows = predict.predict_week(tables, pool, 2025, 5, NOW, model_factory=Mean).set_index("player")
    assert rows.loc["Receiver One", "proj_dk_points"] == 0.0
    assert rows.loc["Rookie Wideout", "proj_dk_points"] > 0
