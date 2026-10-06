import math

import pandas as pd
import pytest
from src.scoring import points_allowed_score


@pytest.mark.parametrize(
    "allowed, points",
    [(0, 10), (1, 7), (6, 7), (7, 4), (13, 4), (14, 1), (20, 1), (21, 0), (27, 0), (28, -1), (34, -1), (35, -4), (52, -4)],
)
def test_points_allowed_tiers(allowed, points):
    assert points_allowed_score(pd.Series([allowed]))[0] == points


def test_no_final_score_scores_nothing():
    assert math.isnan(points_allowed_score(pd.Series([float("nan")]))[0])
