import logging
from datetime import datetime

import pytz


class ESTFormatter(logging.Formatter):
    """Custom logging formatter to use Eastern Time for timestamps."""

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.est_tz = pytz.timezone("America/New_York")

    def formatTime(self, record, datefmt=None):
        # Convert the timestamp to a datetime object in EST
        dt = datetime.fromtimestamp(record.created, self.est_tz)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec="milliseconds")
            except TypeError:
                s = dt.isoformat()
        return s


formatter = ESTFormatter(fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)

log = logging.getLogger("projection-scraper")
log.setLevel(logging.INFO)
log.addHandler(handler)

PROJECTIONS_COLUMN_MAPPINGS = {
    "QB": [
        "player",
        "proj_att",
        "proj_cmp",
        "proj_pass_yds",
        "proj_pass_tds",
        "proj_ints",
        "proj_rush",
        "proj_rush_yds",
        "proj_rush_tds",
        "proj_fl",
        "proj_fpts",
    ],
    "RB": [
        "player",
        "proj_rush",
        "proj_rush_yds",
        "proj_rush_tds",
        "proj_rec",
        "proj_rec_yds",
        "proj_rec_tds",
        "proj_fl",
        "proj_fpts",
    ],
    "WR": [
        "player",
        "proj_rec",
        "proj_rec_yds",
        "proj_rec_tds",
        "proj_rush",
        "proj_rush_yds",
        "proj_rush_tds",
        "proj_fl",
        "proj_fpts",
    ],
    "TE": [
        "player",
        "proj_rec",
        "proj_rec_yds",
        "proj_rec_tds",
        "proj_fl",
        "proj_fpts",
    ],
    "DST": [
        "player",
        "proj_sack",
        "proj_int",
        "proj_fr",
        "proj_ff",
        "proj_dst_td",
        "proj_safety",
        "proj_pass_att",
        "proj_yds_allowed",
        "proj_fpts",
    ],
}

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
    "DST": [
        "player",
        "sack",
        "int",
        "fr",
        "ff",
        "dst_td",
        "safety",
        "spc_td",
        "games",
        "fpts",
        "avg_fpts",
        "rost",
    ],
}
