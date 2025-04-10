import json
import re
from typing import List, Tuple
from io import StringIO

import bs4 as bs
import pandas as pd
import requests
from configs import (
    ADV_STATS_COLUMN_MAPPINGS,
    FPTS_COLUMNS,
    FPTS_COLUMNS_PRE21,
    RZ_COLUMN_MAPPINGS,
    SNAP_COUNTS_COLUMNS,
    STATS_COLUMN_MAPPINGS,
)


def get_current_week(year: int):
    url = "https://www.fantasypros.com/nfl/reports/leaders/"
    params = {
        "year": year,
    }
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    # Find the first column where all values are NaN to get current week
    first_nan_col = df.columns[df.isna().all()][0] if df.isna().all().any() else None
    return int(first_nan_col)


def get_weekly_fpts(position: str, year: int, week: int):
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/reports/leaders/{'ppr-' if position not in ['QB','DST'] else ''}{position.lower()}.php"
    params = {
        "year": year,
    }
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    try:
        df.columns = FPTS_COLUMNS
    except:
        df.columns = FPTS_COLUMNS_PRE21
    df["season"] = year
    df["week"] = week
    df["fpts"] = df[f"week_{week}"].fillna(0).replace("BYE", 0).replace("-", 0).astype(float)
    return df[["player", "position", "season", "week", "fpts"]]


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


def get_weekly_stats(position: str, year: int, week: int, scoring: str = "PPR"):
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/stats/{position.lower()}.php"
    params = {"year": year, "range": "week", "week": week, "scoring": scoring}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = STATS_COLUMN_MAPPINGS[position]
    player = df.player.str.split("(").str[0]
    df["player"] = player
    df["position"] = position
    df["season"] = year
    df["week"] = week
    return df.drop(columns=["games", "avg_fpts"])


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


def get_weekly_adv_stats(position: str, year: int, week: int):
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/advanced-stats-{position.lower()}.php"
    params = {
        "year": year,
        "range": "week",
        "week": week,
    }
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = ADV_STATS_COLUMN_MAPPINGS[position]
    player = df.player.str.split("(").str[0].str.strip()
    df["player"] = player
    df["position"] = position
    df["season"] = year
    df["week"] = week
    return df.drop(columns=["games"])


def get_adv_stats(position: str, year: int, weeks: Tuple[int, int] or List[int, int] = None, view: str = None):
    range = None
    start = None
    end = None
    if weeks:
        range = "custom"
        start = weeks[0]
        end = weeks[1]

    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/advanced-stats-{position.lower()}.php"
    params = {"year": year, "range": range, "start_week": start, "end_week": end, "view": view}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = [
        (
            f"avg_{col}"
            if (
                (col not in ["player", "games", "rtg"])
                and ("/" not in col)
                and ("perc" not in col)
                and ("lng" not in col)
            )
            else col
        )
        for col in ADV_STATS_COLUMN_MAPPINGS[position]
    ]
    player = df.player.str.split("(").str[0].str.strip()
    df["player"] = player
    df["position"] = position
    df["season"] = year
    df["week"] = end + 1
    df[[col for col in df.columns if (("avg" in col))]] = (
        df[[col for col in df.columns if (("avg" in col))]].div(df["games"], axis=0).round(1)
    )
    if position == "QB":
        df["cmp_perc"] = df.cmp_perc.str.strip("%").replace("", 0).astype(float)
    if (position == "WR") or (position == "TE"):
        df["tgt_perc"] = df.tgt_perc.str.strip("%").replace("", 0).astype(float)
    return df


def get_weekly_snap_counts_analysis(position: str, year: int, week: int, scoring: str = "PPR"):
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/reports/snap-count-analysis/{position.lower()}.php"
    params = {"year": year, "range": "week", "week": week, "scoring": scoring, "snaps": 0}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0]
    df.columns = SNAP_COUNTS_COLUMNS
    df["position"] = position
    df["season"] = year
    df["week"] = week
    return df.drop(columns=["games", "snaps/game"])


def get_snap_counts_analysis(
    position: str, year: int, weeks: Tuple[int, int] or List[int, int] = None, scoring: str = "PPR"
):
    range = None
    start = None
    end = None
    if weeks:
        range = "custom"
        start = weeks[0]
        end = weeks[1]

    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/reports/snap-count-analysis/{position.lower()}.php"
    params = {"year": year, "range": range, "start": start, "end": end, "scoring": scoring, "snaps": 0}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0]
    df.columns = SNAP_COUNTS_COLUMNS
    df["avg_fpts"] = round(df.fpts / df.games, 1)
    df["position"] = position
    df["season"] = year
    df["week"] = end + 1
    return df.drop(columns=["snaps", "fpts"])


def get_weekly_rz_stats(position: str, year: int, week: int, scoring: str = "PPR"):
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/red-zone-stats/{position.lower()}.php"
    params = {"year": year, "range": "week", "week": week, "scoring": scoring}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = [
        f"rz_{col}" if col not in ["player", "games", "rost"] else col for col in RZ_COLUMN_MAPPINGS[position]
    ]
    player = df.player.str.split("(").str[0].str.strip()
    df["player"] = player
    df["position"] = position
    df["season"] = year
    df["week"] = week
    return df.drop(columns=["games", "rz_fpts/game"])


def get_rz_stats(position: str, year: int, weeks: Tuple[int, int] or List[int, int] = None, scoring: str = "PPR"):
    range = None
    start = None
    end = None
    if weeks:
        range = "custom"
        start = weeks[0]
        end = weeks[1]

    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/red-zone-stats/{position.lower()}.php"
    params = {"year": year, "range": range, "start_week": start, "end_week": end, "scoring": scoring}
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = [
        f"rz_{col}" if col not in ["player", "games", "rost"] else col for col in RZ_COLUMN_MAPPINGS[position]
    ]
    df.columns = [
        f"avg_{col}" if ((col not in ["player", "games", "rost"]) and ("perc" not in col) and ("/" not in col)) else col
        for col in df.columns
    ]
    player = df.player.str.split("(").str[0].str.strip()
    df["player"] = player
    df["position"] = position
    df["season"] = year
    df["week"] = end + 1
    df[[col for col in df.columns if (("avg" in col))]] = (
        df[[col for col in df.columns if (("avg" in col))]].div(df["games"], axis=0).round(1)
    )
    if position == "QB":
        df["rz_cmp_perc"] = df.rz_cmp_perc.str.strip("%").astype(float)
        df["rz_rush_perc"] = df.rz_rush_perc.str.strip("%").astype(float)
        df["rost"] = df.rost.str.strip("%").astype(float)
    else:
        df["rz_rush_perc"] = df.rz_rush_perc.str.strip("%").astype(float)
        df["rz_rec_perc"] = df.rz_rec_perc.str.strip("%").astype(float)
        df["rz_tgt_perc"] = df.rz_tgt_perc.str.strip("%").astype(float)
        df["rost"] = df.rost.str.strip("%").astype(float)
    return df.drop(columns=["rz_fpts/game"])
