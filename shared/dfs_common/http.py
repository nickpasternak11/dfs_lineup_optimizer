import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def fetch(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 30):
    """GET with retries on transient failures; raises on any non-2xx."""
    response = _http.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response
