import numpy as np
import pandas as pd
import pytest
from dfs_db import PlayerProjection, SnapshotShrankError, replace_weeks
from dfs_db.upsert import _clean
from sqlalchemy.sql import Delete, Insert, Select


class FakeSession:
    """Records statements; answers row-count queries from `existing`."""

    def __init__(self, existing: dict[tuple[int, int], int]):
        self.existing = existing
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        if isinstance(statement, Select):
            params = statement.compile().params
            key = (params["year_1"], params["week_1"])
            return _Scalar(self.existing.get(key, 0))
        return None

    def of_type(self, kind):
        return [s for s in self.statements if isinstance(s, kind)]


class _Scalar:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


def snapshot(year: int, week: int, players: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [year] * players,
            "week": [week] * players,
            "player": [f"Player {i}" for i in range(players)],
            "position": ["QB"] * players,
        }
    )


def test_refuses_a_much_smaller_snapshot_without_deleting():
    session = FakeSession({(2025, 3): 500})

    with pytest.raises(SnapshotShrankError, match="5 rows, current has 500"):
        replace_weeks(session, PlayerProjection, snapshot(2025, 3, 5))

    assert session.of_type(Delete) == []
    assert session.of_type(Insert) == []


def test_replaces_a_same_size_snapshot():
    session = FakeSession({(2025, 3): 5})

    written = replace_weeks(session, PlayerProjection, snapshot(2025, 3, 5))

    assert written == 5
    assert len(session.of_type(Delete)) == 1
    assert len(session.of_type(Insert)) == 1


def test_first_scrape_of_a_week_is_never_blocked():
    session = FakeSession({})
    assert replace_weeks(session, PlayerProjection, snapshot(2025, 3, 5)) == 5


def test_min_ratio_zero_allows_shrinking():
    session = FakeSession({(2025, 3): 500})
    written = replace_weeks(session, PlayerProjection, snapshot(2025, 3, 5), min_ratio=0)
    assert written == 5


def test_one_shrinking_week_blocks_the_whole_write():
    session = FakeSession({(2024, 3): 5, (2025, 3): 500})
    both = pd.concat([snapshot(2024, 3, 5), snapshot(2025, 3, 5)])

    with pytest.raises(SnapshotShrankError):
        replace_weeks(session, PlayerProjection, both)

    # Checked before any delete, so the healthy week is left alone too.
    assert session.of_type(Delete) == []


def test_duplicate_players_are_counted_once():
    # 10 rows but only 5 distinct players: not enough to replace 7.
    session = FakeSession({(2025, 3): 7})
    doubled = pd.concat([snapshot(2025, 3, 5), snapshot(2025, 3, 5)])

    with pytest.raises(SnapshotShrankError):
        replace_weeks(session, PlayerProjection, doubled)


@pytest.mark.parametrize(
    "value, expected",
    [
        (np.int64(7), 7),
        (np.float64(2.5), 2.5),
        (np.float64("nan"), None),
        (float("nan"), None),
        (pd.NaT, None),
        (pd.NA, None),
        (None, None),
        ("Josh Allen", "Josh Allen"),
    ],
)
def test_clean_makes_cells_bindable(value, expected):
    cleaned = _clean(value)
    assert cleaned == expected
    assert not isinstance(cleaned, np.generic)
