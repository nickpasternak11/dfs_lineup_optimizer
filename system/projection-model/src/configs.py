from dfs_common.logs import get_logger

log = get_logger("projection-model")

# The first season the database holds game logs for (GAME_LOG_START_YEAR).
FIRST_TRAIN_SEASON = 2012
# The first season the backtest predicts: our pool's history starts here, so
# it's the first with FantasyPros projections to compare against.
FIRST_TEST_SEASON = 2018

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]

# Stored with each live projection; bump it when the features or model
# change, so the accuracy page can tell versions apart. Version 1 has no
# inactive list yet (#46): live, teammates-out only sees regulars who are
# no longer in the pool, not ones ruled out that week.
MODEL_VERSION = "1"

# Read straight from nflverse on each run rather than stored: only the model
# uses them so far.
NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
SNAP_COUNTS_URL = NFLVERSE + "/snap_counts/snap_counts_{year}.csv.gz"
# The schedule, for its game context (rest days, roof).
SCHEDULE_URL = NFLVERSE + "/schedules/games.csv.gz"
# nflverse's player directory: links snap counts' PFR ids to gsis_ids.
PLAYERS_URL = NFLVERSE + "/players/players.csv.gz"
# nflverse's snap counts start here (its 2012 file is only a header).
FIRST_SNAP_SEASON = 2013
