from pathlib import Path
from types import SimpleNamespace

import pytest
from dfs_common import fantasypros

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def serve(monkeypatch):
    def install(fixture_name: str):
        html = (FIXTURES / fixture_name).read_text()
        monkeypatch.setattr(
            fantasypros, "fetch", lambda url, params=None, headers=None: SimpleNamespace(text=html)
        )

    return install


def test_current_week_is_read_from_the_schedule_caption(serve):
    serve("schedule.html")
    assert fantasypros.get_current_week() == 3


def test_current_week_raises_instead_of_guessing(serve):
    # Regression: this used to fall back to week 1 and overwrite it.
    serve("empty.html")
    with pytest.raises(RuntimeError, match="current week"):
        fantasypros.get_current_week()
