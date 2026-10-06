import re

import bs4

# fetch lives in dfs_common.http; imported here so scrapers can keep using
# dfs_common.fantasypros.fetch.
from dfs_common.http import fetch

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def get_current_week() -> int:
    """Fetch the current NFL week number from FantasyPros.

    Raises rather than guessing: a wrong week would be written over real data
    for that week.
    """
    url = "https://www.fantasypros.com/nfl/schedule.php"
    response = fetch(url, headers={"User-Agent": USER_AGENT})

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    caption = soup.select_one("table#data caption.hidden-aria")
    if caption and (
        match := re.search(r"Week\s+(\d+)", caption.get_text(), re.IGNORECASE)
    ):
        return int(match.group(1))

    raise RuntimeError("Could not find the current week on the FantasyPros schedule")
