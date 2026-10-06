"""One gradient-boosted model per position, predicting DraftKings points."""

from collections.abc import Callable

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from src.features import feature_columns


def make_model() -> HistGradientBoostingRegressor:
    # Missing history (a rookie, a first game back) is a value the trees split
    # on, so no imputation. Small, well-populated leaves backtested better
    # than larger trees (average miss 5.84 against 5.88, ranking 0.381
    # against 0.374); weighting recent seasons more didn't help.
    return HistGradientBoostingRegressor(
        max_iter=500,
        learning_rate=0.03,
        max_leaf_nodes=15,
        min_samples_leaf=150,
        l2_regularization=1.0,
        random_state=0,
    )


def walk_forward(
    features: pd.DataFrame,
    positions: list[str],
    test_seasons: list[int],
    first_train_season: int,
    model_factory: Callable[[], HistGradientBoostingRegressor] = make_model,
) -> pd.DataFrame:
    """Predict each test season with models trained only on the seasons
    before it, the way the model would have run at the time. Returns the
    test rows with a `model` column."""
    predicted = []
    for season in test_seasons:
        train = features[(features.year >= first_train_season) & (features.year < season)]
        test = features[features.year == season]
        for position in positions:
            columns = feature_columns(position)
            fit_rows = train[train.position == position]
            rows = test[test.position == position]
            if fit_rows.empty or rows.empty:
                continue
            model = model_factory().fit(fit_rows[columns], fit_rows.dk_points)
            predicted.append(rows.assign(model=model.predict(rows[columns])))
    return pd.concat(predicted, ignore_index=True) if predicted else features.iloc[0:0].assign(model=[])
