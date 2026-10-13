"""Download nflverse files and shape them into the game-data tables."""

import io
from zoneinfo import ZoneInfo

import pandas as pd
from dfs_common.http import fetch
from src import scoring
from src.configs import (
    FIRST_INJURY_SEASON,
    FIRST_ROSTER_SEASON,
    GAMES_URL,
    INJURIES_URL,
    PLAYER_IDS_URL,
    PLAYER_STATS_URL,
    ROSTERS_URL,
    TEAM_STATS_URL,
)

EASTERN = ZoneInfo("America/New_York")
FANTASY_POSITIONS = ["QB", "RB", "WR", "TE"]


def read_csv(url: str) -> pd.DataFrame:
    # A season file is a few MB; one download, no paging.
    response = fetch(url, timeout=120)
    compression = "gzip" if url.endswith(".gz") else None
    return pd.read_csv(io.BytesIO(response.content), compression=compression, low_memory=False)


def download_season(year: int) -> dict[str, pd.DataFrame]:
    files = {
        "player_stats": read_csv(PLAYER_STATS_URL.format(year=year)),
        "team_stats": read_csv(TEAM_STATS_URL.format(year=year)),
        "games": read_csv(GAMES_URL),
    }
    if year >= FIRST_INJURY_SEASON:
        files["injuries"] = read_csv(INJURIES_URL.format(year=year))
    if year >= FIRST_ROSTER_SEASON:
        files["rosters"] = read_csv(ROSTERS_URL.format(year=year))
    return files


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


def nfl_players(crosswalk: pd.DataFrame) -> pd.DataFrame:
    """GSIS to FantasyPros ids, with each player's bio.

    The crosswalk lists some players twice under different positions with the
    same pair of ids; those collapse to one row. An id paired with two
    different ids is dropped rather than guessed.
    """
    ids = crosswalk.dropna(subset=["gsis_id", "fantasypros_id"])
    ids = ids[ids.gsis_id.astype(str).str.strip().ne("")]
    ids = ids.drop_duplicates(subset=["gsis_id", "fantasypros_id"])
    ids = ids[~ids.gsis_id.duplicated(keep=False) & ~ids.fantasypros_id.duplicated(keep=False)]
    def whole(column: str) -> pd.Series:
        return pd.to_numeric(ids[column], errors="coerce").round().astype("Int64")

    return pd.DataFrame(
        {
            "gsis_id": ids.gsis_id.astype(str),
            "fp_player_id": ids.fantasypros_id.astype(int),
            "player": ids.name,
            "position": ids.position,
            "birthdate": pd.to_datetime(ids.birthdate, errors="coerce").dt.date,
            "height": whole("height"),
            "weight": whole("weight"),
            "college": ids.college,
            "draft_year": whole("draft_year"),
            "draft_round": whole("draft_round"),
            # draft_pick in the crosswalk is the pick within the round.
            "draft_pick": whole("draft_ovr"),
        }
    ).reset_index(drop=True)


GAME_STATUSES = {"Out", "Doubtful", "Questionable", "Probable"}
# The report's wording, shortened. "Probable" was dropped after 2015.
PRACTICE_STATUSES = {
    "Full Participation in Practice": "Full",
    "Limited Participation in Practice": "Limited",
    "Did Not Participate In Practice": "DNP",
}


def injury_reports(injuries: pd.DataFrame) -> pd.DataFrame:
    """One row per player per week: the final game status (NULL when the
    player practiced but wasn't given one) and the week's latest practice
    participation. "Note" rows and other odd values become NULL."""
    df = injuries.dropna(subset=["gsis_id"])
    df = df[df.gsis_id.astype(str).str.strip().ne("")]

    def clean(column: str) -> pd.Series:
        values = df[column].astype("string").str.strip()
        return values.where(values.ne(""))

    out = pd.DataFrame(
        {
            "year": df.season.astype(int),
            "week": df.week.astype(int),
            # Files before 2025 have no season_type; game_type (REG, WC, DIV,
            # CON, SB) is in every year.
            "season_type": df.game_type.where(df.game_type.eq("REG"), "POST"),
            "team": df.team,
            "gsis_id": df.gsis_id.astype(str),
            "player": df.full_name,
            "position": clean("position"),
            "report_status": clean("report_status").where(clean("report_status").isin(GAME_STATUSES)),
            "report_injury": clean("report_primary_injury"),
            "practice_status": clean("practice_status").map(PRACTICE_STATUSES),
            "practice_injury": clean("practice_primary_injury"),
        }
    )
    # A player traded mid-week can appear twice; keep the later team's row.
    return out.drop_duplicates(["year", "week", "gsis_id"], keep="last").reset_index(drop=True)


def weekly_rosters(rosters: pd.DataFrame) -> pd.DataFrame:
    """One row per QB, RB, WR and TE per week: their team and roster status
    (ACT, INA for inactive on game day, RES for injured reserve and the other
    reserve lists, DEV for the practice squad, CUT, RET...), with the NFL's
    code for the detail."""
    df = rosters.dropna(subset=["gsis_id"])
    df = df[df.position.isin(FANTASY_POSITIONS)]
    out = pd.DataFrame(
        {
            "year": df.season.astype(int),
            "week": df.week.astype(int),
            "season_type": df.game_type.where(df.game_type.eq("REG"), "POST"),
            "team": df.team,
            "gsis_id": df.gsis_id.astype(str),
            "player": df.full_name,
            "position": df.position,
            "status": df.status,
            "status_detail": df.status_description_abbr,
        }
    )
    return out.drop_duplicates(["year", "week", "gsis_id"], keep="last").reset_index(drop=True)
