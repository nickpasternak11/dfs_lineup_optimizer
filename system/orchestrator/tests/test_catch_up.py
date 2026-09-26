from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from src.catch_up import catch_up_allowed

EASTERN = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    "moment, allowed",
    [
        (datetime(2026, 9, 28, 20, 0), False),  # Monday: week may be rolling over
        (datetime(2026, 9, 29, 9, 59), False),  # Tuesday before the 9:00/9:30 runs finish
        (datetime(2026, 9, 29, 10, 0), True),
        (datetime(2026, 10, 1, 12, 0), True),  # Thursday
        (datetime(2027, 1, 10, 12, 0), True),  # playoffs
        (datetime(2027, 3, 10, 12, 0), False),  # off-season
        (datetime(2027, 8, 25, 12, 0), False),
    ],
)
def test_catch_up_window(moment, allowed):
    assert catch_up_allowed(moment.replace(tzinfo=EASTERN)) is allowed
