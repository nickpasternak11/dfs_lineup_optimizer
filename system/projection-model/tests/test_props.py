import numpy as np
import pandas as pd
import pytest
from scipy import stats
from src import props


def quote(market, label, price, point=None, player="Josh Allen", book="DraftKings"):
    return {
        "bookmaker": book, "year": 2024, "week": 5, "home": "BUF", "away": "MIA",
        "player": player, "market": market, "label": label, "price": price, "point": point,
    }


def test_american_odds():
    assert list(props.implied_probability(pd.Series([-110, 150, -200]))) == pytest.approx([110 / 210, 0.4, 2 / 3])


def test_the_margin_comes_out_of_each_over_under():
    quotes = pd.DataFrame([
        quote("player_pass_yds", "Over", -110, 249.5),
        quote("player_pass_yds", "Under", -110, 249.5),
        quote("player_pass_yds", "Over", -130, 249.5, book="FanDuel"),
        quote("player_pass_yds", "Under", 110, 249.5, book="FanDuel"),
    ])
    fair = props.fair_over(quotes).set_index("bookmaker").q
    assert fair["DraftKings"] == pytest.approx(0.5)
    p_over, p_under = 130 / 230, 100 / 210
    assert fair["FanDuel"] == pytest.approx(p_over / (p_over + p_under))


def test_poisson_mean_reproduces_the_line():
    line = np.array([0.5, 1.5, 4.5])
    q = np.array([0.4, 0.55, 0.5])
    mean = props.poisson_mean(line, q)
    over = [stats.poisson.sf(np.ceil(l) - 1, m) for l, m in zip(line, mean)]
    assert over == pytest.approx(q, abs=1e-3)
    # An even-money over/under on 0.5 interceptions: P(X >= 1) = 0.5, a mean of ln 2.
    assert props.poisson_mean(np.array([0.5]), np.array([0.5]))[0] == pytest.approx(np.log(2), abs=1e-3)


def test_gamma_mean_sits_above_the_line_and_gives_bonus_chances():
    mean, bonus = props.gamma_mean_and_bonus(np.array([60.5, 95.5]), np.array([0.5, 0.5]), shape=2.4, bonus=100)
    # An even-money line is the median; yards skew right, so the mean is higher.
    assert all(mean > [60.5, 95.5])
    assert 0 < bonus[0] < bonus[1] < 0.5


def test_dk_points_fall_back_to_history_for_missing_markets():
    expected = pd.DataFrame({
        "position": ["WR"], "receiving_yards": [70.0], "receiving_yards_bonus": [0.2],
        "receptions": [np.nan], "td_price_probability": [0.40],
    })
    history = pd.DataFrame({
        "passing_yards": [0.0], "passing_tds": [0.0], "interceptions": [0.0], "rushing_yards": [2.0],
        "receptions": [5.0], "receiving_yards": [55.0], "scoring_tds": [0.3],
    })
    points = props.dk_points(expected, history, td_hold=0.0)
    td = -np.log(1 - 0.40)
    assert points[0] == pytest.approx(70 * 0.1 + 5 + 2 * 0.1 + td * 6 + 3 * 0.2)


def test_td_hold_matches_expected_to_actual_touchdowns():
    probability = pd.Series([0.5] * 100)
    actual = pd.Series([0.5] * 100)
    hold = props.fit_td_hold(probability, actual)
    assert (-np.log1p(-(probability / (1 + hold)))).mean() == pytest.approx(0.5, abs=1e-6)


def test_games_match_the_schedule_not_the_files_week_label():
    quotes = pd.DataFrame([{
        "week": 1, "commence_time": "2024-12-16T01:20:00Z",
        "home_team": "Buffalo Bills", "away_team": "Los Angeles Rams",
    }])
    games = pd.DataFrame({"year": [2024], "week": [15], "home_team": ["BUF"], "away_team": ["LA"]})
    matched = props.attach_games(quotes, games)
    assert (matched.year[0], matched.week[0], matched.away[0]) == (2024, 15, "LA")


def test_players_match_by_name_on_either_team_of_the_game():
    expected = pd.DataFrame({
        "year": 2024, "week": 5, "home": "BUF", "away": "MIA",
        "player": ["Tyreek Hill", "Josh Allen"], "receiving_yards": [80.0, np.nan],
    })
    pool = pd.DataFrame({
        "year": 2024, "week": 5, "player": ["Tyreek Hill", "Josh Allen", "Josh Allen"],
        "nfl_team": ["MIA", "BUF", "JAX"], "position": ["WR", "QB", "LB"],
    })
    matched = props.match_players(expected, pool).set_index("player")
    assert matched.loc["Tyreek Hill", "receiving_yards"] == 80.0
    # The Jaguars' Josh Allen isn't in this game, so only the Bills' matches.
    assert list(matched.loc[["Josh Allen"], "nfl_team"]) == ["BUF"]


def test_a_props_projection_needs_its_positions_core_market():
    df = pd.DataFrame({
        "position": ["QB", "RB", "WR"],
        "passing_yards": [250.0, np.nan, np.nan],
        "rushing_yards": [np.nan, np.nan, 5.0],
        "receiving_yards": [np.nan, 20.0, 60.0],
    })
    assert list(props.has_core_market(df)) == [True, False, True]
