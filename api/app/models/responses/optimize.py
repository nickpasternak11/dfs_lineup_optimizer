from app.models.responses.projections import ProjectionRecord


class LineupPlayer(ProjectionRecord):
    """A player in an optimized lineup.

    Same fields as a projection record, except proj_fpts is the score the
    lineup was optimized on: the second and third lineups blend in avg_fpts.
    """


# One list of nine players per lineup.
OptimizeResponse = list[list[LineupPlayer]]
