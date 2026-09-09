from io import StringIO

import pandas as pd
import requests


def get_current_week(year: int):
    url = "https://www.fantasypros.com/nfl/reports/leaders/"
    params = {"year": year}
    r = requests.get(
        url,
        params=params,
        timeout=30,
    )

    try:
        tables = pd.read_html(StringIO(r.text), attrs={"id": "data"})
        df = tables[0].iloc[:, 1:]
    except ValueError:
        return 1  # Return 1 if no tables are found

    # Find the first column where all values are NaN to get current week
    week = int(df.columns[df.isna().all()][0]) if df.isna().all().any() else 1
    return week
