from dfs_common.logs import get_logger

log = get_logger("projection-model")

# The first season the database holds game logs for (GAME_LOG_START_YEAR).
FIRST_TRAIN_SEASON = 2012
# The first season the backtest predicts: our pool's history starts here, so
# it's the first with FantasyPros projections to compare against.
FIRST_TEST_SEASON = 2018

POSITIONS = ["QB", "RB", "WR", "TE", "DST"]
