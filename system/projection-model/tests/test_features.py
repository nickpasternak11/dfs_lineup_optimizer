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


def team_week(week, players):
    """players: (gsis_id, position, targets, carries) for one BUF game against MIA."""
    return [log(week, gsis_id, position, "BUF", "MIA", 5.0, targets=t, carries=c) for gsis_id, position, t, c in players]


def test_a_missing_regulars_share_is_vacated_for_their_teammates():
    regulars = [("wr1", "WR", 6, 0), ("wr2", "WR", 3, 0), ("te1", "TE", 1, 0), ("rb1", "RB", 0, 9), ("rb2", "RB", 0, 1)]
    rows = team_week(1, regulars) + team_week(2, regulars)
    # Week 3: the top receiver and the lead back are out.
    rows += team_week(3, [("wr2", "WR", 6, 0), ("te1", "TE", 3, 0), ("rb2", "RB", 0, 8)])
    logs = pd.DataFrame(rows)
    features = player_features(logs, games_for(logs))

    week2 = row(features, "wr2", 2)
    assert (week2.vacated_target_share, week2.vacated_carry_share) == (0.0, 0.0)

    wr2, te1 = row(features, "wr2", 3), row(features, "te1", 3)
    assert wr2.vacated_target_share == pytest.approx(0.6)  # wr1's 6 of 10 targets
    assert wr2.vacated_carry_share == pytest.approx(0.9)  # rb1's 9 of 10 carries
    # By position: the receiver's vacated targets are a WR's; the tight end's aren't.
    assert wr2.vacated_position_target_share == pytest.approx(0.6)
    assert te1.vacated_position_target_share == 0.0


def test_bit_players_and_long_gone_players_vacate_nothing():
    # wr3 drew 10% of targets, then 5%: about 7% weighted to the recent game,
    # under the 8% that makes a regular. wr4 was a regular, then left.
    rows = team_week(1, [("wr1", "WR", 6, 0), ("wr3", "WR", 1, 0), ("wr4", "WR", 3, 0)])
    rows += team_week(2, [("wr1", "WR", 16, 0), ("wr3", "WR", 1, 0), ("wr4", "WR", 3, 0)])
    rows += [r for w in range(3, 8) for r in team_week(w, [("wr1", "WR", 10, 0)])]
    logs = pd.DataFrame(rows)
    features = player_features(logs, games_for(logs))
    wr4_role = row(features, "wr1", 3).vacated_target_share
    assert wr4_role > 0.15  # only wr4's share; wr3's isn't counted
    assert row(features, "wr1", 5).vacated_target_share == pytest.approx(wr4_role)
    # VACATED_WINDOW (3) team games after wr4's last, wr4 is no longer expected.
    assert row(features, "wr1", 6).vacated_target_share == 0.0


def test_snap_share_history_comes_from_earlier_games(logs):
    snaps = pd.DataFrame({
        "year": 2025, "week": [1, 2, 3], "gsis_id": "wr1", "team": "BUF",
        "offense_snaps": [50, 60, 70], "snap_share": [0.7, 0.8, 0.95],
    })
    features = player_features(logs, games_for(logs), snaps)
    assert pd.isna(row(features, "wr1", 1).snap_share_short)
    assert row(features, "wr1", 2).snap_share_short == pytest.approx(0.7)
    assert 0.7 < row(features, "wr1", 3).snap_share_short < 0.8  # week 3's own 0.95 isn't in it
    # Without snap counts (before 2012) the features are missing, not zero.
    assert pd.isna(row(player_features(logs, games_for(logs)), "wr1", 3).snap_share_short)


def test_game_context_from_each_teams_side():
    from src.features import game_context
    schedule = pd.DataFrame({
        "game_id": ["outdoors", "indoors"], "home_team": ["BUF", "DET"], "away_team": ["MIA", "GB"],
        "home_rest": [7, 10], "away_rest": [4, 7], "roof": ["outdoors", "dome"],
        "wind": [18.0, None], "temp": [28.0, None],
    })
    context = game_context(schedule).set_index("team")
    assert (context.loc["MIA", "rest_days"], context.loc["MIA", "wind"], context.loc["MIA", "dome"]) == (4, 18.0, 0.0)
    # Indoors: no wind, no temperature.
    assert (context.loc["GB", "wind"], context.loc["GB", "dome"]) == (0.0, 1.0)
    assert pd.isna(context.loc["DET", "temp"])
