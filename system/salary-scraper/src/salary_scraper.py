import pandas as pd
from dfs_common.fantasypros import get_current_week
from dfs_common.season import current_season_year
from dfs_db import PlayerSalary, replace_weeks, session_scope
from dfs_db.upsert import DEFAULT_MIN_RATIO
from src.configs import log
from src.utils import get_salary_data

SALARY_INT_COLUMNS = ["salary", "prev_salary", "salary_change"]


class SalaryScraper:
    def __init__(self):
        self.current_week = get_current_week()
        self.fp_year = current_season_year()

    def scrape(self, year: int | None = None, allow_shrink: bool = False) -> None:
        # The salary-changes page honours `year` but always serves the current
        # NFL week, so the week is never a choice here: any other label would
        # file this week's salaries under the wrong week.
        year = self.fp_year if year is None else year
        week = self.current_week

        df = get_salary_data(year=year)
        if df.empty:
            raise RuntimeError(f"Salary table was empty for year={year}, week={week}")

        df = df.assign(year=year, week=week)
        # parse_currency yields floats; the columns are INTEGER in Postgres and
        # Int64 keeps the missing values as NA rather than NaN.
        df[SALARY_INT_COLUMNS] = df[SALARY_INT_COLUMNS].round().astype("Int64")

        # The page gives only a weekday and time; get_salary_data places them
        # in the current calendar week. That's right for the live season and
        # a fabricated date for any past one, where it would also make the
        # optimizer treat the games as already started.
        if year != self.fp_year:
            df["kickoff"] = pd.NaT

        log.info("Saving salary data..")
        with session_scope() as session:
            rows = replace_weeks(
                session,
                PlayerSalary,
                df,
                min_ratio=0 if allow_shrink else DEFAULT_MIN_RATIO,
            )
        log.info("Upserted %s salary rows for year=%s, week=%s", rows, year, week)


if __name__ == "__main__":
    SalaryScraper().scrape()
