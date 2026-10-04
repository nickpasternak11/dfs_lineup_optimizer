import os

import requests
from dfs_common.logs import get_logger

log = get_logger("alerts")

# Discord rejects messages longer than this.
MAX_LENGTH = 2000


def send_alert(message: str) -> bool:
    """Post `message` to ALERT_WEBHOOK_URL; returns whether it was delivered.

    Works with Slack and Discord incoming webhooks. Unset URL means alerts are
    only logged. Never raises: a broken webhook must not break the caller.
    """
    url = os.getenv("ALERT_WEBHOOK_URL")
    if not url:
        return False

    message = message[:MAX_LENGTH]
    # Slack reads "text" and Discord reads "content"; send both.
    try:
        response = requests.post(url, json={"text": message, "content": message}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        log.error("Could not send alert: %s", error)
        return False
    return True
