import logging
import os
from enum import Enum

from datetime import datetime
import pytz

class ESTFormatter(logging.Formatter):
    """Custom logging formatter to use Eastern Time for timestamps."""
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.est_tz = pytz.timezone('America/New_York')

    def formatTime(self, record, datefmt=None):
        # Convert the timestamp to a datetime object in EST
        dt = datetime.fromtimestamp(record.created, self.est_tz)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()
        return s

formatter = ESTFormatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

log = logging.getLogger("api")
log.setLevel(logging.INFO)
log.addHandler(handler)


APP_NAME = "DFSLineupOptimizer"
SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))


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
