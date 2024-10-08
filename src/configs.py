import logging

from enum import Enum


log = logging.getLogger("dfs-optimizer")


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


FPTS_COLUMNS = ["player", "position", "team"] + [f"week_{week}" for week in range(1, 19)] + ["avg_fpts", "ttl_fpts"]
FPTS_COLUMNS_PRE21 = (
    ["player", "position", "team"] + [f"week_{week}" for week in range(1, 18)] + ["avg_fpts", "ttl_fpts"]
)

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

ADV_STATS_COLUMN_MAPPINGS = {
    "QB": [
        "player",
        "games",
        "cmp",
        "att",
        "cmp_perc",
        "pass_yds",
        "pass_yds/att",
        "pass_air_yds",
        "pass_air_yds/att",
        "pass_10_plus",
        "pass_20_plus",
        "pass_30_plus",
        "pass_40_plus",
        "pass_50_plus",
        "pkt_time",
        "sacks",
        "knockdowns",
        "hurries",
        "blitz",
        "poor_pass",
        "drops",
        "rz_att",
        "rtg",
    ],
    "RB": [
        "player",
        "games",
        "rush",
        "rush_yds",
        "rush_yds/rush",
        "rush_yds_bcon",
        "rush_yds_bcon/rush",
        "rush_yds_acon",
        "rush_yds_acon/rush",
        "brkn_tkl",
        "tkl_loss",
        "tkl_loss_yds",
        "lng_td",
        "rush_10_plus",
        "rush_20_plus",
        "rush_30_plus",
        "rush_40_plus",
        "rush_50_plus",
        "rush_lng",
        "rec",
        "tgt",
        "rz_tgt",
        "rec_yds_acon",
    ],
    "WR": [
        "player",
        "games",
        "rec",
        "rec_yds",
        "rec_yds/rec",
        "rec_yds_bc",
        "rec_yds_bc/rec",
        "rec_air_yds",
        "rec_air_yds/rec",
        "rec_yds_ac",
        "rec_yds_ac/rec",
        "rec_yds_acon",
        "rec_yds_acon/rec",
        "brkn_tkl",
        "tgt",
        "tgt_perc",
        "catchable",
        "drops",
        "rz_tgt",
        "rec_10_plus",
        "rec_20_plus",
        "rec_30_plus",
        "rec_40_plus",
        "rec_50_plus",
        "rec_lng",
    ],
    "TE": [
        "player",
        "games",
        "rec",
        "rec_yds",
        "rec_yds/rec",
        "rec_yds_bc",
        "rec_yds_bc/rec",
        "rec_air_yds",
        "rec_air_yds/rec",
        "rec_yds_ac",
        "rec_yds_ac/rec",
        "rec_yds_acon",
        "rec_yds_acon/rec",
        "brkn_tkl",
        "tgt",
        "tgt_perc",
        "catchable",
        "drops",
        "rz_tgt",
        "rec_10_plus",
        "rec_20_plus",
        "rec_30_plus",
        "rec_40_plus",
        "rec_50_plus",
        "rec_lng",
    ],
}


SNAP_COUNTS_COLUMNS = [
    "player",
    "team",
    "games",
    "snaps",
    "snaps/game",
    "snap_perc",
    "snap_rush_perc",
    "snap_tgt_perc",
    "touch_perc",
    "util_perc",
    "fpts",
    "fpts/100_snaps",
]

RZ_COLUMN_MAPPINGS = {
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
        "rush_perc",
        "fl",
        "games",
        "fpts",
        "fpts/game",
        "rost",
    ],
    "RB": [
        "player",
        "rush",
        "rush_yds",
        "rush_yds/rush",
        "rush_tds",
        "rush_perc",
        "rec",
        "tgt",
        "rec_perc",
        "rec_yds",
        "rec_yds/rec",
        "rec_tds",
        "tgt_perc",
        "fl",
        "games",
        "fpts",
        "fpts/game",
        "rost",
    ],
    "WR": [
        "player",
        "rec",
        "tgt",
        "rec_perc",
        "rec_yds",
        "rec_yds/rec",
        "rec_tds",
        "tgt_perc",
        "rush",
        "rush_yds",
        "rush_tds",
        "rush_perc",
        "fl",
        "games",
        "fpts",
        "fpts/game",
        "rost",
    ],
    "TE": [
        "player",
        "rec",
        "tgt",
        "rec_perc",
        "rec_yds",
        "rec_yds/rec",
        "rec_tds",
        "tgt_perc",
        "rush",
        "rush_yds",
        "rush_tds",
        "rush_perc",
        "fl",
        "games",
        "fpts",
        "fpts/game",
        "rost",
    ],
}
