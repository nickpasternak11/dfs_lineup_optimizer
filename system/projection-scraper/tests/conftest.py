from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_fetch(monkeypatch):
    """Serve a fixture file in place of a FantasyPros request.

    Returns the list of (url, params) calls so tests can check what was asked.
    """
    calls = []

    def install(fixture_name: str):
        html = (FIXTURES / fixture_name).read_text()

        def fetch(url, params=None, headers=None):
            calls.append((url, params))
            return SimpleNamespace(text=html)

        monkeypatch.setattr("src.utils.fetch", fetch)
        return calls

    return install
