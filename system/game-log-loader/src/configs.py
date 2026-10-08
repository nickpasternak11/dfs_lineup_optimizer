from dfs_common.logs import get_logger

log = get_logger("game-log-loader")

# nflverse publishes each dataset as a GitHub release; the season files are
# rebuilt nightly in-season.
NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
PLAYER_STATS_URL = NFLVERSE + "/stats_player/stats_player_week_{year}.csv.gz"
TEAM_STATS_URL = NFLVERSE + "/stats_team/stats_team_week_{year}.csv.gz"
GAMES_URL = NFLVERSE + "/schedules/games.csv.gz"
# The NFL's weekly injury reports: one row per listed player per week, with
# the final game status and that week's practice participation. Rebuilt about
# twice a day in season. Plain CSV: the .csv.gz only exists from 2023.
INJURIES_URL = NFLVERSE + "/injuries/injuries_{year}.csv"

# DynastyProcess's crosswalk of player ids across sites; the only public source
# linking nflverse's GSIS ids to FantasyPros ids.
PLAYER_IDS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_playerids.csv"
)

# Seasons with weekly stats in the format this loader reads.
FIRST_SEASON = 1999
# Injury reports start here.
FIRST_INJURY_SEASON = 2009
