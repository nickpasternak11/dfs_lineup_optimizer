import os
import glob
import json
import re
from io import StringIO
from typing import List, Tuple

import bs4 as bs
import pandas as pd
import requests
from app.configs.configs import STATS_COLUMN_MAPPINGS


def get_latest_week() -> int:
    pattern = "/app/data/salaries/dk_salary_*_w*.csv"
    files = glob.glob(pattern)
    if not files:
        return 1
    latest_file = max(files, key=os.path.getctime)
    week_number = latest_file.split("_w")[-1].split(".")[0]
    return int(week_number)


def get_weekly_rankings(position: str, year: int, week: int):
    rankings_list = []
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/rankings/{'ppr-' if position not in ['QB','DST'] else ''}{position.lower()}.php"
    params = {"year": year, "week": week}
    r = requests.get(url, params=params)
    cxt = bs.BeautifulSoup(r.text, features="lxml")
    script_tags = cxt.find_all("script", attrs={"type": "text/javascript"})
    for script_tag in script_tags:
        script_text = script_tag.text.strip()
        if "var ecrData =" in script_text:
            ecrData_match = re.search(r"var ecrData = (.*?});", script_text)
            if ecrData_match:
                players = json.loads(ecrData_match.group(1))["players"]
                for player in players:
                    try:
                        player_name = player["player_name"]
                        position = player["player_position_id"]
                        rank = player["rank_ecr"]
                        rank_min = player["rank_min"]
                        rank_max = player["rank_max"]
                        rank_avg = player["rank_ave"]
                        rank_std = player["rank_std"]
                        grade = player["start_sit_grade"]
                        fpts = player.get("r2p_pts", 0.0)
                        rankings_list.append(
                            {
                                "player": str(player_name),
                                "position": str(position),
                                "year": int(year),
                                "week": int(week),
                                "rank": int(rank),
                                "min_rank": int(rank_min),
                                "max_rank": int(rank_max),
                                "avg_rank": float(rank_avg),
                                "std_rank": float(rank_std),
                                "grade": str(grade),
                                "proj_fpts": float(fpts),
                            }
                        )
                    except:
                        pass
    return pd.DataFrame(rankings_list)


def get_stats(position: str, year: int, weeks: Tuple[int, int] or List[int, int] = None, scoring: str = "PPR"):
    range = None
    start = None
    end = None
    if weeks:
        range = "custom"
        start = weeks[0]
        end = weeks[1]

    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/stats/{position.lower()}.php"
    params = {"year": year, "range": range, "start_week": start, "end_week": end, "scoring": scoring}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = [
        (
            f"avg_{col}"
            if ((col not in ["player", "cmp_perc", "games", "lng", "fpts", "avg_fpts", "rost"]) and ("/" not in col))
            else col
        )
        for col in STATS_COLUMN_MAPPINGS[position]
    ]
    player = df.player.str.split("(").str[0].str.strip()
    df["player"] = player
    df["position"] = position
    df["season"] = year
    df["week"] = end + 1
    df["rost"] = df.rost.str.strip("%").astype(float)
    df[[col for col in df.columns if (("avg" in col) and (col != "avg_fpts"))]] = (
        df[[col for col in df.columns if (("avg" in col) and (col != "avg_fpts"))]].div(df["games"], axis=0).round(1)
    )
    return df.drop(columns="fpts")
