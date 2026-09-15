import json
import re
from io import StringIO

import bs4
import pandas as pd
import requests
from src.configs import PROJECTIONS_COLUMN_MAPPINGS, STATS_COLUMN_MAPPINGS


def get_current_week() -> int:
    """Fetch the current NFL week number from FantasyPros.

    Returns default_week if the request fails or parsing finds no match.
    """
    url = "https://www.fantasypros.com/nfl/schedule.php"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        caption = soup.select_one("table#data caption.hidden-aria")

        if caption and (
            match := re.search(r"Week\s+(\d+)", caption.get_text(), re.IGNORECASE)
        ):
            return int(match.group(1))

    except (requests.RequestException, ValueError) as e:
        print(f"Warning: Failed to fetch current week ({e}). Defaulting to 1.")

    return 1


def get_weekly_rankings(position: str, year: int, week: int):
    rankings_list = []
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/rankings/{'ppr-' if position not in ['QB', 'DST'] else ''}{position.lower()}.php"
    params = {"year": year, "week": week}
    r = requests.get(url, params=params)
    cxt = bs4.BeautifulSoup(r.text, features="lxml")
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


def get_weekly_projections(
    position: str,
    year: int,
    week: int,
    scoring: str = "PPR",
):
    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/projections/{position.lower()}.php"
    params = {
        "year": year,
        "week": week,
        "scoring": scoring,
    }
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0]
    df.columns = PROJECTIONS_COLUMN_MAPPINGS[position]
    player_col = (
        df.player if position == "DST" else df.player.str.split().str[:-1].str.join(" ")
    )
    df["player"] = player_col
    df["position"] = position
    df["season"] = year
    df["week"] = week
    return df


def get_stats(
    position: str,
    year: int,
    weeks: tuple[int, int] or list[int, int] = None,
    scoring: str = "PPR",
):
    range = None
    start = None
    end = None
    if weeks:
        range = "custom"
        start = weeks[0]
        end = weeks[1]

    # Handle first week of the season (week 1)
    if end is not None and end == 0:
        start = 1
        end = 18
        year = year - 1

    position = position.upper()
    url = f"https://www.fantasypros.com/nfl/stats/{position.lower()}.php"
    params = {
        "year": year,
        "range": range,
        "start_week": start,
        "end_week": end,
        "scoring": scoring,
    }
    r = requests.get(url, params=params)
    df = pd.io.html.read_html(StringIO(r.text), attrs={"id": "data"})[0].iloc[:, 1:]
    df.columns = [
        (
            f"avg_{col}"
            if (
                (
                    col
                    not in [
                        "player",
                        "cmp_perc",
                        "games",
                        "lng",
                        "fpts",
                        "avg_fpts",
                        "rost",
                    ]
                )
                and ("/" not in col)
            )
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
        df[[col for col in df.columns if (("avg" in col) and (col != "avg_fpts"))]]
        .div(df["games"], axis=0)
        .round(1)
    )
    return df.drop(columns="fpts")
