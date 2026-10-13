"""Sportsbook player props turned into expected stats and DraftKings points.

Over/under markets carry both sides' prices, so each book's margin comes out
exactly: the fair chance of the over is its implied probability over the
two sides' sum. That chance and the line give the stat's mean under an
assumed distribution: Poisson for counts (receptions, passing TDs,
interceptions), gamma for yards, whose spread is set from past seasons and
which also gives the chance of DraftKings' 100- and 300-yard bonuses.
Anytime-TD prices are one-sided, so their margin is a parameter (`td_hold`).
"""

import numpy as np
import pandas as pd
from dfs_db.names import name_key
from scipy import stats

# The Odds API's team names, as nflverse codes.
TEAM_CODES = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}

# Market -> (game-log column, distribution, bonus threshold or None)
OVER_UNDER = {
    "player_pass_yds": ("passing_yards", "gamma", 300),
    "player_rush_yds": ("rushing_yards", "gamma", 100),
    "player_reception_yds": ("receiving_yards", "gamma", 100),
    "player_receptions": ("receptions", "poisson", None),
    "player_pass_tds": ("passing_tds", "poisson", None),
    "player_pass_interceptions": ("interceptions", "poisson", None),
}
ANYTIME_TD = "player_anytime_td"
# A game, once attach_games has matched the quote to the schedule.
GAME = ["year", "week", "home", "away"]

# Players whose spread (coefficient of variation) sets the gamma shape: a
# season of 8+ games averaging at least this much.
CV_MINIMUM_AVERAGE = {"passing_yards": 150, "rushing_yards": 30, "receiving_yards": 30}


def implied_probability(price: pd.Series) -> pd.Series:
    """American odds to the probability they imply (margin included)."""
    price = price.astype(float)
    return np.where(price > 0, 100 / (price + 100), -price / (-price + 100))


def fair_over(quotes: pd.DataFrame) -> pd.DataFrame:
    """One row per book, game, player, market and line, with the fair chance
    of the over: its implied probability over the two sides' sum."""
    keys = ["bookmaker", *GAME, "player", "market", "point"]
    sides = quotes[quotes.market.isin(OVER_UNDER)].assign(p=lambda d: implied_probability(d.price))
    wide = sides.pivot_table(index=keys, columns="label", values="p", aggfunc="first").dropna(subset=["Over", "Under"])
    return (wide.Over / (wide.Over + wide.Under)).rename("q").reset_index()


def gamma_shapes(logs: pd.DataFrame) -> dict[str, float]:
    """Gamma shape (1 / CV squared) for each yardage stat, from regulars'
    week-to-week spread in the given seasons."""
    shapes = {}
    regular = logs[logs.season_type == "REG"]
    for column, minimum in CV_MINIMUM_AVERAGE.items():
        seasons = regular.groupby(["gsis_id", "year"])[column].agg(["mean", "std", "size"])
        seasons = seasons[(seasons["size"] >= 8) & (seasons["mean"] >= minimum)]
        cv = (seasons["std"] / seasons["mean"]).median()
        shapes[column] = float(1 / cv**2)
    return shapes


def poisson_mean(line: np.ndarray, q: np.ndarray) -> np.ndarray:
    """The Poisson mean at which P(X > line) = q, for half-point lines."""
    grid = np.linspace(0.005, 25, 5000)
    out = np.full(len(line), np.nan)
    for threshold in np.unique(np.ceil(line)):
        rows = np.ceil(line) == threshold
        over = stats.poisson.sf(threshold - 1, grid)  # rises with the mean
        out[rows] = np.interp(q[rows], over, grid)
    return out


def gamma_mean_and_bonus(line: np.ndarray, q: np.ndarray, shape: float, bonus: float) -> tuple[np.ndarray, np.ndarray]:
    """The gamma (with this shape) whose P(X > line) = q: its mean, and its
    chance of reaching the bonus threshold."""
    q = np.clip(q, 0.01, 0.99)
    scale = line / stats.gamma.isf(q, shape)
    return shape * scale, stats.gamma.sf(bonus / scale, shape)


def expected_stats(quotes: pd.DataFrame, shapes: dict[str, float]) -> pd.DataFrame:
    """One row per game and player: each market's expected stat (and bonus
    chance for yards), the median over books and lines. Columns are the
    game-log names, plus `{column}_bonus` and `td_price_probability`.
    `quotes` must have been through attach_games."""
    lines = fair_over(quotes)
    rows = []
    for market, (column, distribution, bonus) in OVER_UNDER.items():
        subset = lines[lines.market == market]
        if subset.empty:
            continue
        line, q = subset.point.to_numpy(float), subset.q.to_numpy(float)
        if distribution == "poisson":
            values = {column: poisson_mean(line, q)}
        else:
            mean, chance = gamma_mean_and_bonus(line, q, shapes[column], bonus)
            values = {column: mean, f"{column}_bonus": chance}
        rows.append(subset[[*GAME, "player"]].assign(**values))
    expected = pd.concat(rows).groupby([*GAME, "player"]).median()

    anytime = quotes[(quotes.market == ANYTIME_TD) & (quotes.label == "Yes")]
    anytime = anytime.assign(p=implied_probability(anytime.price))
    td = anytime.groupby([*GAME, "player"]).p.median().rename("td_price_probability")
    return expected.join(td, how="outer").reset_index()


def dk_points(expected: pd.DataFrame, history: pd.DataFrame, td_hold: float) -> pd.Series:
    """DraftKings points from expected stats. A market the books didn't post
    for a player falls back to `history`, the same columns averaged over the
    player's recent games (with `scoring_tds` for rushing plus receiving
    TDs); `td_hold` is the anytime-TD price's margin. Rows align with
    `expected`."""
    def stat(column):
        return expected[column].fillna(history[column]) if column in expected else history[column]

    def bonus(column):
        name = f"{column}_bonus"
        return expected[name].fillna(0.0) if name in expected else 0.0

    td_probability = (expected.td_price_probability / (1 + td_hold)).clip(upper=0.95)
    scoring_tds = (-np.log1p(-td_probability)).fillna(history.scoring_tds)
    return (
        stat("passing_yards") * 0.04 + stat("passing_tds") * 4 - stat("interceptions")
        + stat("rushing_yards") * 0.1 + stat("receptions") + stat("receiving_yards") * 0.1
        + scoring_tds * 6
        + 3 * (bonus("passing_yards") + bonus("rushing_yards") + bonus("receiving_yards"))
    )


def attach_games(quotes: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Each quote's NFL season, week and teams, matched on its season and its
    home and away teams (a pairing happens once per season)."""
    kickoff = pd.to_datetime(quotes.commence_time, utc=True)
    quotes = quotes.assign(
        year=np.where(kickoff.dt.month <= 3, kickoff.dt.year - 1, kickoff.dt.year),
        home=quotes.home_team.map(TEAM_CODES),
        away=quotes.away_team.map(TEAM_CODES),
    )
    schedule = games[["year", "week", "home_team", "away_team"]].rename(columns={"home_team": "home", "away_team": "away"})
    return quotes.drop(columns="week").merge(schedule, on=["year", "home", "away"])


def match_players(expected: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    """Props per pool row: the player with the same name key on either team
    of that week's game. Names that match twice are dropped."""
    expected = expected.assign(key=expected.player.map(name_key))
    pool = pool.assign(key=pool.player.map(name_key))
    candidates = []
    for side in ("home", "away"):
        candidates.append(
            pool.merge(
                expected.drop(columns="player"),
                left_on=["year", "week", "key", "nfl_team"],
                right_on=["year", "week", "key", side],
            )
        )
    matched = pd.concat(candidates, ignore_index=True)
    unique = matched.groupby(["year", "week", "player"]).player.transform("size") == 1
    return matched[unique].drop(columns=["key", "home", "away"])


# The market a position's props projection needs before it counts as one:
# without it, it would mostly be the player's history.
CORE_MARKET = {"QB": "passing_yards", "RB": "rushing_yards", "WR": "receiving_yards", "TE": "receiving_yards"}


def has_core_market(df: pd.DataFrame) -> pd.Series:
    out = pd.Series(False, index=df.index)
    for position, column in CORE_MARKET.items():
        if column in df:
            out |= (df.position == position) & df[column].notna()
    return out


def fit_td_hold(probability: pd.Series, actual_tds: pd.Series) -> float:
    """The anytime-TD margin at which the prices' expected touchdowns match
    the touchdowns scored, by bisection."""
    low, high = 0.0, 1.0
    for _ in range(40):
        hold = (low + high) / 2
        expected = -np.log1p(-(probability / (1 + hold)).clip(upper=0.95))
        if expected.mean() > actual_tds.mean():
            low = hold
        else:
            high = hold
    return (low + high) / 2
