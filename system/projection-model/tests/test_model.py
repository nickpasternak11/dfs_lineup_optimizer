import pandas as pd
from src.features import feature_columns
from src.model import walk_forward


class Recorder:
    """Stands in for the model: remembers what it was trained on and
    predicts the training seasons' latest year, so leaks would show."""

    fits = []

    def fit(self, X, y):
        self.trained_on = sorted(X.index.map(self.years.get).unique())
        Recorder.fits.append(self.trained_on)
        return self

    def predict(self, X):
        return [max(self.trained_on)] * len(X)


def test_each_season_is_predicted_by_models_trained_on_earlier_seasons_only():
    rows = []
    for year in range(2015, 2020):
        for position in ("WR", "DST"):
            rows.append({"year": year, "week": 1, "position": position, "dk_points": 10.0,
                         **{c: 1.0 for c in feature_columns(position)}})
    features = pd.DataFrame(rows)
    Recorder.years = features.year.to_dict()
    Recorder.fits = []

    predicted = walk_forward(features, ["WR", "DST"], [2018, 2019], first_train_season=2016, model_factory=Recorder)

    assert sorted(predicted.year.unique()) == [2018, 2019]
    assert Recorder.fits == [[2016, 2017], [2016, 2017], [2016, 2017, 2018], [2016, 2017, 2018]]
    # 2019 was predicted by models whose latest season was 2018.
    assert set(predicted[predicted.year == 2019].model) == {2018}
