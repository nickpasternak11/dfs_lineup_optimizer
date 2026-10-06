from datetime import datetime, timezone

import pandas as pd
import pytest
import requests
from src import lineups

NOW = datetime(2025, 10, 12, 13, 0, tzinfo=timezone.utc)


def lineup(prefix, points):
    return [
        {"player": f"{prefix}{i}", "position": "WR", "team": "BUF", "salary": 5000, "proj_fpts": points}
        for i in range(9)
    ]


def test_each_lineup_player_is_a_row_with_its_sources_own_projection():
    pool = pd.DataFrame({
        "player": [f"fp{i}" for i in range(9)] + [f"m{i}" for i in range(9)],
        "proj_fpts": [10.0] * 9 + [8.0] * 9,
        "model_fpts": [11.0] * 9 + [12.5] * 9,
    }).set_index("player")
    suggested = {
        # The blends report what they were optimized on, not the plain projection.
        "fantasypros": [lineup("fp", 10.0), lineup("fp", 9.8), lineup("fp", 9.6)],
        "model": [lineup("m", 12.5), lineup("m", 12.3), lineup("m", 12.1)],
    }
    rows = lineups.snapshot_rows(suggested, pool, 2025, 6, NOW)

    assert len(rows) == 2 * 3 * 9
    blend = rows[(rows.source == "fantasypros") & (rows.strategy == "blend_80_20")].iloc[0]
    assert (blend.projection, blend.optimized_points) == (10.0, 9.6)
    model = rows[(rows.source == "model") & (rows.strategy == "projection")]
    assert set(model.projection) == {12.5}
    assert list(model.slot) == list(range(9))
    assert (rows.generated_at == NOW).all() and (rows.week == 6).all()


class Response:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)

    def json(self):
        return self._body


def test_a_source_the_api_cant_optimize_is_skipped(monkeypatch):
    def fake_post(url, payload):
        if payload["projection_source"] == "model":
            raise requests.HTTPError(response=Response(400, {"detail": "Our model hasn't projected"}))
        return Response(200, [lineup("fp", 10.0)] * 3)

    monkeypatch.setattr(lineups, "post", fake_post)
    assert list(lineups.suggested_lineups(2025, 6)) == ["fantasypros"]


def test_other_api_failures_are_raised(monkeypatch):
    def fake_post(url, payload):
        raise requests.HTTPError(response=Response(500, "boom"))

    monkeypatch.setattr(lineups, "post", fake_post)
    with pytest.raises(requests.HTTPError):
        lineups.suggested_lineups(2025, 6)
