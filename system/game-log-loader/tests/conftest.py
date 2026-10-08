from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def nflverse_files():
    """Real nflverse rows (2025 week 5, plus a few schedule edge cases)."""

    def read(name: str) -> pd.DataFrame:
        return pd.read_csv(FIXTURES / f"{name}.csv", low_memory=False)

    return {
        "player_stats": read("player_stats"),
        "team_stats": read("team_stats"),
        "games": read("games"),
        "player_ids": read("player_ids"),
        "injuries": read("injuries"),
    }
