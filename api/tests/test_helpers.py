import pandas as pd

from app.helpers.optimize import dataframe_to_records


def test_missing_values_become_none_for_json():
    df = pd.DataFrame(
        {
            "player": ["A", "B"],
            "kickoff": pd.to_datetime(["2026-09-27T17:00:00Z", None], utc=True),
            "avg_fpts": [12.5, float("nan")],
            "salary_change": pd.array([300, None], dtype="Int64"),
        }
    )

    first, second = dataframe_to_records(df)

    assert first["kickoff"] == "2026-09-27T17:00:00+0000"
    assert first["avg_fpts"] == 12.5
    assert second["kickoff"] is None
    assert second["avg_fpts"] is None
    assert second["salary_change"] is None


def test_empty_frame_gives_no_records():
    assert dataframe_to_records(pd.DataFrame()) == []
