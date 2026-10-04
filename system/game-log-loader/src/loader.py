from dfs_db import DstGameLog, NflGame, PlayerGameLog, PlayerIdMap, replace_matching, session_scope
from dfs_db.upsert import DEFAULT_MIN_RATIO
from src import nflverse
from src.configs import log


def load_season(year: int, allow_shrink: bool = False) -> None:
    """Replace one season's games and game logs with nflverse's current files.

    nflverse rebuilds each season file in full (stat corrections included), so
    the season is replaced rather than upserted, in one transaction.
    """
    min_ratio = 0 if allow_shrink else DEFAULT_MIN_RATIO
    log.info("Downloading nflverse data for %s..", year)
    data = nflverse.download_season(year)

    games = nflverse.nfl_games(data["games"], year)
    players = nflverse.player_game_logs(data["player_stats"])
    dsts = nflverse.dst_game_logs(data["team_stats"], data["games"])
    if players.empty:
        raise RuntimeError(f"nflverse has no player stats for {year} yet")

    with session_scope() as session:
        season = {"year": year}
        written = {
            "games": replace_matching(session, NflGame, games, season, min_ratio),
            "player logs": replace_matching(session, PlayerGameLog, players, season, min_ratio),
            "DST logs": replace_matching(session, DstGameLog, dsts, season, min_ratio),
        }
    weeks = f"weeks {players.week.min()}-{players.week.max()}"
    log.info(
        "Loaded %s %s: %s",
        year,
        weeks,
        ", ".join(f"{count} {name}" for name, count in written.items()),
    )


def load_player_ids(allow_shrink: bool = False) -> None:
    """Replace the GSIS-to-FantasyPros id map with the current crosswalk."""
    ids = nflverse.player_id_map(nflverse.download_player_ids())
    with session_scope() as session:
        count = replace_matching(
            session, PlayerIdMap, ids, {}, 0 if allow_shrink else DEFAULT_MIN_RATIO
        )
    log.info("Loaded %s player id mappings", count)
