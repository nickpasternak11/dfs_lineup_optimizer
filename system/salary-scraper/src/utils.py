from io import StringIO

import pandas as pd
import requests


def get_current_week(year: int):
    url = "https://www.fantasypros.com/nfl/reports/leaders/"
    params = {
        "year": year,
    }
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    # Find the first column where all values are NaN to get current week
    week = int(df.columns[df.isna().all()][0]) if df.isna().all().any() else 19
    return week
