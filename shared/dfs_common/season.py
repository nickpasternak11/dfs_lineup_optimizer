from datetime import date


def current_season_year(today: date | None = None) -> int:
    """The NFL season in progress on `today`.

    Seasons span the new year: January and February belong to the season that
    started the previous September. FantasyPros and every table here key rows
    by this season year, not the calendar year.
    """
    today = today or date.today()
    return today.year - 1 if today.month in [1, 2] else today.year
