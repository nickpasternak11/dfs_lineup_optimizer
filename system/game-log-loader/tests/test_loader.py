from contextlib import contextmanager

import pytest
from dfs_db import DstGameLog, NflGame, PlayerGameLog, PlayerIdMap
from src import loader


@pytest.fixture
def writes(monkeypatch, nflverse_files):
    """Serve fixture files instead of nflverse, and record each replace."""
    calls = []
    monkeypatch.setattr(
        loader.nflverse,
        "download_season",
        lambda year: {k: nflverse_files[k] for k in ("player_stats", "team_stats", "games")},
    )
    monkeypatch.setattr(loader.nflverse, "download_player_ids", lambda: nflverse_files["player_ids"])

    @contextmanager
    def fake_session_scope():
        yield "session"

    def fake_replace(session, model, df, where, min_ratio):
        calls.append((model, len(df), where, min_ratio))
        return len(df)

    monkeypatch.setattr(loader, "session_scope", fake_session_scope)
    monkeypatch.setattr(loader, "replace_matching", fake_replace)
    return calls


def test_a_season_replaces_its_games_and_logs(writes):
    loader.load_season(2025)

    assert [model for model, *_ in writes] == [NflGame, PlayerGameLog, DstGameLog]
    assert all(where == {"year": 2025} for _, _, where, _ in writes)
    assert all(min_ratio == 0.8 for *_, min_ratio in writes)
    counts = {model: rows for model, rows, *_ in writes}
    assert counts[PlayerGameLog] == 4  # the K and OLB are dropped
    assert counts[DstGameLog] == 10


def test_allow_shrink_disables_the_guard(writes):
    loader.load_season(2025, allow_shrink=True)
    assert all(min_ratio == 0 for *_, min_ratio in writes)


def test_a_season_without_player_stats_fails_before_writing(writes, monkeypatch, nflverse_files):
    monkeypatch.setattr(
        loader.nflverse,
        "download_season",
        lambda year: {
            "player_stats": nflverse_files["player_stats"].iloc[0:0],
            "team_stats": nflverse_files["team_stats"],
            "games": nflverse_files["games"],
        },
    )
    with pytest.raises(RuntimeError, match="no player stats for 2027"):
        loader.load_season(2027)
    assert writes == []


def test_the_id_map_replaces_the_whole_table(writes):
    loader.load_player_ids()
    ((model, rows, where, _),) = writes
    assert (model, where) == (PlayerIdMap, {})
    assert rows == 4
