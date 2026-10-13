"""DraftKings NFL classic scoring, applied to nflverse weekly stat lines.

Player scoring was checked against nflverse's own full-PPR column across the
2025 season: the two differ by exactly DraftKings' rules (the 300/100/100-yard
bonuses, -1 rather than -2 for interceptions and lost fumbles) on every
player-week except those with an offensive fumble-recovery touchdown, which
DraftKings scores and nflverse's PPR leaves out.
"""

import numpy as np
import pandas as pd

YARDAGE_BONUS = 3


def player_points(stats: pd.DataFrame) -> pd.Series:
    """DraftKings points for QB/RB/WR/TE stat lines (player_game_logs columns)."""
    s = stats
    passing = s.passing_yards * 0.04 + s.passing_tds * 4 - s.interceptions
    rushing = s.rushing_yards * 0.1 + s.rushing_tds * 6
    receiving = s.receptions + s.receiving_yards * 0.1 + s.receiving_tds * 6
    bonuses = YARDAGE_BONUS * (
        (s.passing_yards >= 300).astype(int)
        + (s.rushing_yards >= 100).astype(int)
        + (s.receiving_yards >= 100).astype(int)
    )
    other = s.other_tds * 6 + s.two_point_conversions * 2 - s.fumbles_lost
    return (passing + rushing + receiving + bonuses + other).round(2)


# (most points allowed, DraftKings points) -- 0 allowed is worth 10, 35+ is -4.
POINTS_ALLOWED_TIERS = [(0, 10), (6, 7), (13, 4), (20, 1), (27, 0), (34, -1)]
POINTS_ALLOWED_FLOOR = -4


def points_allowed_score(points_allowed: pd.Series) -> pd.Series:
    """The points-allowed component; NaN when the game has no final score."""
    score = pd.Series(POINTS_ALLOWED_FLOOR, index=points_allowed.index, dtype=float)
    for most, points in reversed(POINTS_ALLOWED_TIERS):
        score[points_allowed <= most] = points
    score[points_allowed.isna()] = np.nan
    return score


def dst_points(stats: pd.DataFrame) -> pd.Series:
    """DraftKings points for team defense/special teams (dst_game_logs columns).

    Points allowed are the opponent's final score. DraftKings excludes points
    the defense didn't give up (a pick-six thrown by its own offense), which
    team-level data can't separate, so the occasional week can be off by a
    tier.
    """
    s = stats
    plays = (
        s.sacks
        + s.interceptions * 2
        + s.fumble_recoveries * 2
        + (s.defensive_tds + s.return_tds) * 6
        + s.safeties * 2
        + s.blocked_kicks * 2
    )
    return (plays + points_allowed_score(s.points_allowed)).round(2)
