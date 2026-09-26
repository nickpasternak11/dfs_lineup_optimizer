import logging

from dfs_common.logs import ESTFormatter, get_logger


def test_repeated_calls_attach_one_handler():
    # Every module that imports a service's configs calls get_logger; a second
    # handler would print every line twice.
    first = get_logger("dfs-test-logger")
    second = get_logger("dfs-test-logger")
    assert first is second
    assert len(first.handlers) == 1
    assert first.level == logging.INFO


def test_timestamps_are_eastern_time():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", None, None)
    record.created = 1790528400.0  # 2026-09-27 17:00:00 UTC
    stamp = ESTFormatter().formatTime(record)
    assert stamp.startswith("2026-09-27T13:00:00.000")
    assert stamp.endswith("-04:00")
