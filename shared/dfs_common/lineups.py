"""The optimizer settings for the lineups saved for the weekly review."""

# Every saved lineup, on each projection source and before and after
# Sunday's swap, and the best lineup in hindsight it's measured against:
# the QB stacked with at least one of his own WRs/TEs, no DST facing the
# lineup's own players, and no second TE in FLEX. Teammates' results move
# together and a defense pulls against the offense it faces (#51), and that's
# how tournament lineups are built. Keyword arguments of
# DFSLineupOptimizer.optimize, and fields of the API's optimize request.
SAVED_LINEUP_SETTINGS = {"stack_qb_count": 1, "avoid_dst_vs_players": True, "avoid_te_flex": True}
