import pytest

from app.configs.configs import MAX_AUTO_WORKERS, resolve_worker_count


@pytest.mark.parametrize("raw", [None, "", "auto", " AUTO "])
def test_auto_workers_follow_cpu_count(raw):
    assert resolve_worker_count(raw, cpu_count=2) == 2


def test_auto_workers_are_capped():
    # Every worker has its own DB pool; a big host must not exhaust Postgres.
    assert resolve_worker_count("auto", cpu_count=64) == MAX_AUTO_WORKERS


def test_auto_workers_without_cpu_count():
    assert resolve_worker_count(None, cpu_count=None) == 1


def test_explicit_worker_count_is_not_capped():
    assert resolve_worker_count("12", cpu_count=2) == 12


@pytest.mark.parametrize("raw", ["0", "-1", "many"])
def test_invalid_worker_count_raises(raw):
    with pytest.raises(ValueError):
        resolve_worker_count(raw, cpu_count=4)
