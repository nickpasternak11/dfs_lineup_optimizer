from datetime import date

import pytest
from dfs_common.season import current_season_year


@pytest.mark.parametrize(
    "today, season",
    [
        (date(2026, 9, 10), 2026),  # opening week
        (date(2026, 12, 31), 2026),
        (date(2027, 1, 10), 2026),  # late regular season / playoffs
        (date(2027, 2, 14), 2026),  # Super Bowl
        (date(2027, 3, 1), 2027),  # offseason counts as the coming season
    ],
)
def test_january_and_february_belong_to_the_previous_season(today, season):
    assert current_season_year(today) == season
