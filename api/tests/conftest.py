import pandas as pd
import pytest

from app.db.optimize import DFSLineupOptimizer

# (player, position, team, proj_fpts). Every player costs $5,000 by default,
# so nine of them fit under the $50,000 cap and projections alone decide.
BASE_POOL = [
    ("QB A1", "QB", "A", 20.0),
    ("QB B1", "QB", "B", 17.0),
    ("QB C1", "QB", "C", 14.0),
    ("RB A1", "RB", "A", 18.0),
    ("RB B1", "RB", "B", 16.0),
    ("RB C1", "RB", "C", 14.0),
    ("RB D1", "RB", "D", 12.0),
    ("RB E1", "RB", "E", 10.0),
    ("WR A1", "WR", "A", 17.0),
    ("WR A2", "WR", "A", 13.0),
    ("WR B1", "WR", "B", 15.0),
    ("WR C1", "WR", "C", 14.0),
    ("WR D1", "WR", "D", 12.0),
    ("WR E1", "WR", "E", 11.0),
    ("TE A1", "TE", "A", 10.0),
    ("TE B1", "TE", "B", 8.0),
    ("TE C1", "TE", "C", 6.0),
    ("DST A", "DST", "A", 8.0),
    ("DST B", "DST", "B", 7.0),
    ("DST C", "DST", "C", 6.0),
]


@pytest.fixture
def pool() -> pd.DataFrame:
    df = pd.DataFrame(BASE_POOL, columns=["player", "position", "team", "proj_fpts"])
    df["avg_fpts"] = df["proj_fpts"]
    df["salary"] = 5000
    df["kickoff"] = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
    return df


@pytest.fixture
def make_optimizer():
    """Build an optimizer over an in-memory pool, bypassing the database."""

    def build(df: pd.DataFrame) -> DFSLineupOptimizer:
        # year and week given, so the constructor never queries for the week.
        optimizer = DFSLineupOptimizer(year=2025, week=3)
        optimizer._projections_df = df.reset_index(drop=True)
        return optimizer

    return build
