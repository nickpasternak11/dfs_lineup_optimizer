import requests
from dfs_common import alerts


class Recorder:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def post(self, url, json, timeout):
        self.calls.append((url, json))
        if self.error:
            raise self.error
        return self

    def raise_for_status(self):
        pass


def test_no_webhook_configured_sends_nothing(monkeypatch):
    recorder = Recorder()
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(alerts.requests, "post", recorder.post)
    assert alerts.send_alert("backup failed") is False
    assert recorder.calls == []


def test_posts_a_slack_and_discord_compatible_payload(monkeypatch):
    recorder = Recorder()
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example/abc")
    monkeypatch.setattr(alerts.requests, "post", recorder.post)

    assert alerts.send_alert("backup failed") is True
    assert recorder.calls == [
        ("https://hooks.example/abc", {"text": "backup failed", "content": "backup failed"})
    ]


def test_long_messages_are_truncated_to_discords_limit(monkeypatch):
    recorder = Recorder()
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example/abc")
    monkeypatch.setattr(alerts.requests, "post", recorder.post)
    alerts.send_alert("x" * 5000)
    assert len(recorder.calls[0][1]["content"]) == alerts.MAX_LENGTH


def test_a_broken_webhook_never_raises(monkeypatch):
    recorder = Recorder(error=requests.ConnectionError("unreachable"))
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example/abc")
    monkeypatch.setattr(alerts.requests, "post", recorder.post)
    assert alerts.send_alert("backup failed") is False
