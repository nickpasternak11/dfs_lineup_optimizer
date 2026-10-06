import pandas as pd
import pytest
from src.features import PLAYER_FEATURES, dst_features, player_features, team_lines

STAT_COLUMNS = [
    "attempts", "carries", "targets", "receptions", "passing_yards", "passing_tds",
    "interceptions", "rushing_yards", "rushing_tds", "receiving_yards", "receiving_tds", "fumbles_lost",
]


def log(week, gsis_id, position, team, opponent, dk_points, targets=0, carries=0, year=2025):
    row = dict.fromkeys(STAT_COLUMNS, 0)
    row.update(
        year=year, week=week, gsis_id=gsis_id, player=gsis_id, position=position, team=team,
        opponent=opponent, game_id=f"{year}_{week:02d}_{opponent}_{team}", season_type="REG",
        dk_points=dk_points, targets=targets, carries=carries,
    )
    return row


def games_for(logs: pd.DataFrame) -> pd.DataFrame:
    """One game per game_id, the player's team at home, favored by 3 in a 44 total."""
    first = logs.drop_duplicates("game_id")
    return pd.DataFrame({
        "game_id": first.game_id, "year": first.year, "week": first.week,
        "home_team": first.team, "away_team": first.opponent,
        "spread_line": 3.0, "total_line": 44.0,
    })


@pytest.fixture
def logs() -> pd.DataFrame:
    rows = []
    for week, points in [(1, 10.0), (2, 20.0), (3, 30.0), (4, 5.0)]:
        rows.append(log(week, "wr1", "WR", "BUF", "MIA", points, targets=6))
        rows.append(log(week, "wr2", "WR", "BUF", "MIA", 4.0, targets=2))
        rows.append(log(week, "fb", "FB", "BUF", "MIA", 1.0, carries=1))
    return pd.DataFrame(rows)


def row(features, gsis_id, week):
    return features[(features.gsis_id == gsis_id) & (features.week == week)].iloc[0]


def test_history_comes_from_earlier_games_only(logs):
    features = player_features(logs, games_for(logs))
    assert pd.isna(row(features, "wr1", 1).dk_points_short)  # no earlier games
    assert row(features, "wr1", 2).dk_points_short == 10.0
    # Week 3's own 30 points mustn't leak into its features.
    week3 = row(features, "wr1", 3)
    assert 10.0 < week3.dk_points_short < 20.0
    changed = logs.copy()
    changed.loc[(changed.gsis_id == "wr1") & (changed.week == 3), "dk_points"] = 99.0
    assert row(player_features(changed, games_for(changed)), "wr1", 3).dk_points_short == week3.dk_points_short


def test_shares_and_counts(logs):
    features = player_features(logs, games_for(logs))
    week2 = row(features, "wr1", 2)
    assert week2.target_share_short == pytest.approx(0.75)  # 6 of the team's 8 targets in week 1
    assert (week2.prior_games, week2.season_games, week2.weeks_off) == (1, 1, 1)


def test_a_fullback_counts_as_a_running_back(logs):
    features = player_features(logs, games_for(logs))
    assert set(features[features.gsis_id == "fb"].position) == {"RB"}


def test_opponent_allowed_uses_its_earlier_games(logs):
    features = player_features(logs, games_for(logs))
    # MIA allowed 14 to WRs in week 1 (10 + 4) and 24 in week 2 (20 + 4).
    assert pd.isna(row(features, "wr1", 1).opp_allowed)
    assert row(features, "wr1", 3).opp_allowed == pytest.approx(19.0)


def test_lines_from_each_teams_side():
    games = pd.DataFrame({
        "game_id": ["g"], "year": [2025], "week": [1], "home_team": ["BUF"], "away_team": ["NE"],
        "spread_line": [7.0], "total_line": [49.5],
    })
    lines = team_lines(games).set_index("team")
    assert (lines.loc["BUF", "implied_total"], lines.loc["BUF", "spread"], lines.loc["BUF", "home"]) == (28.25, -7.0, 1.0)
    assert (lines.loc["NE", "implied_total"], lines.loc["NE", "opp_implied_total"], lines.loc["NE", "spread"]) == (21.25, 28.25, 7.0)


def test_every_feature_is_built(logs):
    features = player_features(logs, games_for(logs))
    assert set(PLAYER_FEATURES) <= set(features.columns)
    assert row(features, "wr1", 2).implied_total == pytest.approx(23.5)


def test_defenses_get_their_own_history_and_the_offense_they_face():
    dst = pd.DataFrame([
        {"year": 2025, "week": w, "team": team, "opponent": opp, "game_id": f"g{w}",
         "season_type": "REG", "sacks": 2.0, "interceptions": 1, "fumble_recoveries": 0,
         "points_allowed": 17, "dk_points": pts}
        for w, team, opp, pts in [(1, "BUF", "MIA", 8.0), (1, "MIA", "BUF", 2.0), (2, "BUF", "NYJ", 12.0), (2, "NYJ", "BUF", 1.0)]
    ])
    games = pd.DataFrame({
        "game_id": ["g1", "g2"], "year": 2025, "week": [1, 2],
        "home_team": ["BUF", "BUF"], "away_team": ["MIA", "NYJ"], "spread_line": 3.0, "total_line": 44.0,
    })
    features = dst_features(dst, games)
    nyj = features[(features.team == "NYJ") & (features.week == 2)].iloc[0]
    # The Jets face BUF, whose offense gave up 2 to MIA's defense in week 1.
    assert nyj.opp_allowed == 2.0
    buf = features[(features.team == "BUF") & (features.week == 2)].iloc[0]
    assert buf.dk_points_short == 8.0
