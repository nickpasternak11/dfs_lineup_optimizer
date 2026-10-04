"""Download nflverse files and shape them into the game-data tables."""

import io
from zoneinfo import ZoneInfo

import pandas as pd
from dfs_common.http import fetch
from src import scoring
from src.configs import GAMES_URL, PLAYER_IDS_URL, PLAYER_STATS_URL, TEAM_STATS_URL

EASTERN = ZoneInfo("America/New_York")
FANTASY_POSITIONS = ["QB", "RB", "WR", "TE"]


def read_csv(url: str) -> pd.DataFrame:
    # A season file is a few MB; one download, no paging.
    response = fetch(url, timeout=120)
    compression = "gzip" if url.endswith(".gz") else None
    return pd.read_csv(io.BytesIO(response.content), compression=compression, low_memory=False)


def download_season(year: int) -> dict[str, pd.DataFrame]:
    return {
        "player_stats": read_csv(PLAYER_STATS_URL.format(year=year)),
        "team_stats": read_csv(TEAM_STATS_URL.format(year=year)),
        "games": read_csv(GAMES_URL),
    }


def download_player_ids() -> pd.DataFrame:
    return read_csv(PLAYER_IDS_URL)


def _counts(frame: pd.DataFrame, columns: dict[str, list[str]]) -> pd.DataFrame:
    """Sum nflverse columns into ours; missing values count as zero."""
    return pd.DataFrame(
        {
            ours: frame[theirs].fillna(0).sum(axis=1).round().astype(int)
            for ours, theirs in columns.items()
        },
        index=frame.index,
    )


PLAYER_STAT_COLUMNS = {
    "completions": ["completions"],
    "attempts": ["attempts"],
    "passing_yards": ["passing_yards"],
    "passing_tds": ["passing_tds"],
    "interceptions": ["passing_interceptions"],
    "carries": ["carries"],
    "rushing_yards": ["rushing_yards"],
    "rushing_tds": ["rushing_tds"],
    "targets": ["targets"],
    "receptions": ["receptions"],
    "receiving_yards": ["receiving_yards"],
    "receiving_tds": ["receiving_tds"],
    # Every lost fumble, kick returns included: DraftKings deducts them all.
    "fumbles_lost": ["fumbles_lost_total"],
    "two_point_conversions": [
        "passing_2pt_conversions",
        "rushing_2pt_conversions",
        "receiving_2pt_conversions",
    ],
    "other_tds": ["special_teams_tds", "fumble_recovery_tds"],
}


def player_game_logs(player_stats: pd.DataFrame) -> pd.DataFrame:
    """One row per QB/RB/WR/TE per week, with DraftKings points."""
    stats = player_stats[player_stats.position_group.isin(FANTASY_POSITIONS)]
    logs = pd.concat(
        [
            pd.DataFrame(
                {
                    "year": stats.season.astype(int),
                    "week": stats.week.astype(int),
                    "gsis_id": stats.player_id,
                    "player": stats.player_display_name,
                    "position": stats.position,
                    "team": stats.team,
                    "opponent": stats.opponent_team,
                    "game_id": stats.game_id,
                    "season_type": stats.season_type,
                    "ppr_points": stats.fantasy_points_ppr,
                }
            ),
            _counts(stats, PLAYER_STAT_COLUMNS),
        ],
        axis=1,
    )
    logs["dk_points"] = scoring.player_points(logs)
    return logs.reset_index(drop=True)


DST_STAT_COLUMNS = {
    "interceptions": ["def_interceptions"],
    "fumble_recoveries": ["fumble_recovery_opp"],
    "defensive_tds": ["def_tds"],
    "return_tds": ["special_teams_tds"],
    "safeties": ["def_safeties"],
    "blocked_kicks": ["def_punt_blocks", "def_fg_blocks", "def_pat_blocks"],
}


def dst_game_logs(team_stats: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """One row per team defense per week, with DraftKings points.

    Weeks whose game has no final score yet are left out rather than scored
    without their points-allowed component.
    """
    scores = games.set_index("game_id")[["home_team", "home_score", "away_score"]]
    joined = team_stats.join(scores, on="game_id")
    points_allowed = joined.away_score.where(joined.team == joined.home_team, joined.home_score)

    logs = pd.concat(
        [
            pd.DataFrame(
                {
                    "year": joined.season.astype(int),
                    "week": joined.week.astype(int),
                    "team": joined.team,
                    "opponent": joined.opponent_team,
                    "game_id": joined.game_id,
                    "season_type": joined.season_type,
                    "sacks": joined.def_sacks.fillna(0).astype(float),
                    "points_allowed": points_allowed,
                }
            ),
            _counts(joined, DST_STAT_COLUMNS),
        ],
        axis=1,
    )
    logs = logs[logs.points_allowed.notna()].copy()
    logs["points_allowed"] = logs.points_allowed.astype(int)
    logs["dk_points"] = scoring.dst_points(logs)
    return logs.reset_index(drop=True)


def nfl_games(games: pd.DataFrame, year: int) -> pd.DataFrame:
    """The season's games. nflverse gives kickoff as an Eastern date and time."""
    season = games[games.season == year]
    local = pd.to_datetime(season.gameday + " " + season.gametime.fillna("00:00"), errors="coerce")
    kickoff = local.dt.tz_localize(EASTERN, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    return pd.DataFrame(
        {
            "game_id": season.game_id,
            "year": season.season.astype(int),
            "week": season.week.astype(int),
            "game_type": season.game_type,
            "kickoff": kickoff,
            "away_team": season.away_team,
            "home_team": season.home_team,
            "away_score": season.away_score.astype("Int64"),
            "home_score": season.home_score.astype("Int64"),
            "spread_line": season.spread_line,
            "total_line": season.total_line,
            "away_moneyline": season.away_moneyline.astype("Int64"),
            "home_moneyline": season.home_moneyline.astype("Int64"),
        }
    ).reset_index(drop=True)


def player_id_map(crosswalk: pd.DataFrame) -> pd.DataFrame:
    """GSIS to FantasyPros ids.

    The crosswalk lists some players twice under different positions with the
    same pair of ids; those collapse to one row. An id paired with two
    different ids is dropped rather than guessed.
    """
    ids = crosswalk.dropna(subset=["gsis_id", "fantasypros_id"])
    ids = ids[ids.gsis_id.astype(str).str.strip().ne("")]
    ids = ids.drop_duplicates(subset=["gsis_id", "fantasypros_id"])
    ids = ids[~ids.gsis_id.duplicated(keep=False) & ~ids.fantasypros_id.duplicated(keep=False)]
    return pd.DataFrame(
        {
            "gsis_id": ids.gsis_id.astype(str),
            "fp_player_id": ids.fantasypros_id.astype(int),
            "player": ids.name,
            "position": ids.position,
        }
    ).reset_index(drop=True)
