import glob
import os


def get_latest_week(year: int | None = None) -> int:
    pattern = f"/app/data/salaries/dk_salary_{year if year else '*'}_w*.csv"
    files = glob.glob(pattern)
    if not files:
        return 1
    latest_file = max(files, key=os.path.getctime)
    week_number = latest_file.split("_w")[-1].split(".")[0]
    return int(week_number)
