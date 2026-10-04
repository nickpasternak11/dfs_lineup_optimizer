import re

import bs4
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_http = requests.Session()
_http.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
    ),
)


def fetch(url: str, params: dict | None = None, headers: dict | None = None):
    """GET with retries on transient failures; raises on any non-2xx."""
    response = _http.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response


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
