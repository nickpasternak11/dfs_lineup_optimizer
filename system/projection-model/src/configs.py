import os

from dfs_common.logs import get_logger

log = get_logger("projection-model")

# The first season the database holds game logs for (GAME_LOG_START_YEAR).
FIRST_TRAIN_SEASON = 2012
# The first season the backtest predicts: our pool's history starts here, so
# it's the first with FantasyPros projections to compare against.
FIRST_TEST_SEASON = 2018

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]

# Stored with each live projection; bump it when the features or model
# change, so the accuracy page can tell versions apart.
# 1: no injury data; live, teammates-out saw almost no one missing.
# 2: the weekly injury reports (#46): each player's own status and practice
#    as features, teammates listed Out or Doubtful (or on another team) as
#    missing, and Out or Doubtful players projected at 0. Game-day inactives
#    (who among the Questionable sits) aren't known.
MODEL_VERSION = "2"

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

# The API, which owns the optimizer; the lineups step asks it for lineups.
API_URL = os.getenv("API_URL", "http://dfs-api:8080")
