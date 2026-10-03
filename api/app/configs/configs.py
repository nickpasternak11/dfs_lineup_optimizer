import os
from enum import Enum

from dfs_common.logs import get_logger

log = get_logger("api")


APP_NAME = "DFSLineupOptimizer"
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))

# Above this many cores, "auto" stops adding workers: each one holds its own
# DB pool (DB_POOL_SIZE + DB_MAX_OVERFLOW connections), and Postgres allows 100.
MAX_AUTO_WORKERS = 4


def resolve_worker_count(raw: str | None, cpu_count: int | None) -> int:
    """Number of uvicorn worker processes for API_WORKERS.

    The optimizer's model building is CPU-bound Python, so one process tops out
    at about one core however many threads serve requests. Unset, empty or
    "auto" means one worker per core, capped at MAX_AUTO_WORKERS.
    """
    if raw is None or raw.strip().lower() in ("", "auto"):
        return max(1, min(cpu_count or 1, MAX_AUTO_WORKERS))
    workers = int(raw)
    if workers < 1:
        raise ValueError(f"API_WORKERS must be at least 1, got {workers}")
    return workers


API_WORKERS = resolve_worker_count(os.getenv("API_WORKERS"), os.cpu_count())


class NFLTeam(Enum):
    ARIZONA_CARDINALS = "Cardinals"
    ATLANTA_FALCONS = "Falcons"
    BALTIMORE_RAVENS = "Ravens"
    BUFFALO_BILLS = "Bills"
    CAROLINA_PANTHERS = "Panthers"
    CHICAGO_BEARS = "Bears"
    CINCINNATI_BENGALS = "Bengals"
    CLEVELAND_BROWNS = "Browns"
    DALLAS_COWBOYS = "Cowboys"
    DENVER_BRONCOS = "Broncos"
    DETROIT_LIONS = "Lions"
    GREEN_BAY_PACKERS = "Packers"
    HOUSTON_TEXANS = "Texans"
    INDIANAPOLIS_COLTS = "Colts"
    JACKSONVILLE_JAGUARS = "Jaguars"
    KANSAS_CITY_CHIEFS = "Chiefs"
    LAS_VEGAS_RAIDERS = "Raiders"
    LOS_ANGELES_CHARGERS = "Chargers"
    LOS_ANGELES_RAMS = "Rams"
    MIAMI_DOLPHINS = "Dolphins"
    MINNESOTA_VIKINGS = "Vikings"
    NEW_ENGLAND_PATRIOTS = "Patriots"
    NEW_ORLEANS_SAINTS = "Saints"
    NEW_YORK_GIANTS = "Giants"
    NEW_YORK_JETS = "Jets"
    PHILADELPHIA_EAGLES = "Eagles"
    PITTSBURGH_STEELERS = "Steelers"
    SAN_FRANCISCO_49ERS = "49ers"
    SEATTLE_SEAHAWKS = "Seahawks"
    TAMPA_BAY_BUCCANEERS = "Buccaneers"
    TENNESSEE_TITANS = "Titans"
    WASHINGTON_COMMANDERS = "Commanders"


STATS_COLUMN_MAPPINGS = {
    "QB": [
        "player",
        "cmp",
        "att",
        "cmp_perc",
        "pass_yds",
        "pass_yds/att",
        "pass_tds",
        "ints",
        "sacks",
        "rush",
        "rush_yds",
        "rush_tds",
        "fl",
        "games",
        "fpts",
        "avg_fpts",
        "rost",
    ],
    "RB": [
        "player",
        "rush",
        "rush_yds",
        "rush_yds/rush",
        "lng",
        "20+",
        "rush_tds",
        "rec",
        "tgt",
        "rec_yds",
        "rec_yds/rec",
        "rec_tds",
        "fl",
        "games",
        "fpts",
        "avg_fpts",
        "rost",
    ],
    "WR": [
        "player",
        "rec",
        "tgt",
        "rec_yds",
        "rec_yds/rec",
        "lng",
        "20+",
        "rec_tds",
        "rush",
        "rush_yds",
        "rush_tds",
        "fl",
        "games",
        "fpts",
        "avg_fpts",
        "rost",
    ],
    "TE": [
        "player",
        "rec",
        "tgt",
        "rec_yds",
        "rec_yds/rec",
        "lng",
        "20+",
        "rec_tds",
        "rush",
        "rush_yds",
        "rush_tds",
        "fl",
        "games",
        "fpts",
        "avg_fpts",
        "rost",
    ],
    "DST": ["player", "sack", "int", "fr", "ff", "dst_td", "safety", "spc_td", "games", "fpts", "avg_fpts", "rost"],
}
