import textwrap

import pytest
import schedule
import src.orchestrator as orchestrator
from src.orchestrator import ScraperOrchestrator


@pytest.fixture
def jobs_dir(tmp_path, monkeypatch):
    """A jobs directory with a fake scraper that reports what it received."""
    scraper = tmp_path / "fake-scraper"
    (scraper / "src").mkdir(parents=True)
    (scraper / "src" / "__init__.py").write_text("")
    (scraper / "src" / "identity.py").write_text('NAME = "fake scraper src"\n')
    (scraper / "main.py").write_text(
        textwrap.dedent(
            """
            import os
            import sys

            from src.identity import NAME

            print(NAME)
            print("args:", " ".join(sys.argv[1:]))
            print("password:", os.environ.get("POSTGRES_PASSWORD"))
            sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
            """
        )
    )
    monkeypatch.setattr(orchestrator, "JOBS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def instance():
    created = ScraperOrchestrator()
    yield created
    schedule.clear()


def test_scraper_runs_with_its_own_src_package_and_args(instance, jobs_dir, caplog, monkeypatch):
    # The orchestrator has a `src` package too; the child must import its own.
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")

    assert instance.run_scraper("fake-scraper", ["--start-year", "2018"]) is True

    logged = caplog.text
    assert "[fake-scraper] fake scraper src" in logged
    assert "[fake-scraper] args: --start-year 2018" in logged
    assert "[fake-scraper] password: secret" in logged  # DB credentials inherited
    assert "fake-scraper completed successfully" in logged


def test_failed_scraper_is_reported_without_raising(instance, jobs_dir, caplog, monkeypatch):
    monkeypatch.setenv("FAKE_EXIT", "3")
    assert instance.run_scraper("fake-scraper") is False
    assert "fake-scraper exited with status code 3" in caplog.text


def test_missing_scraper_is_reported_without_raising(instance, jobs_dir, caplog):
    assert instance.run_scraper("no-such-scraper") is False
    assert "Could not start no-such-scraper" in caplog.text


def test_backfill_runs_both_scrapers_from_the_start_year(instance, monkeypatch):
    calls = []
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: calls.append((name, args)))
    monkeypatch.setattr(orchestrator, "BACKFILL_START_YEAR", "2019")

    instance.run_backfill()

    assert calls == [
        ("salary-scraper", ["--start-year", "2019"]),
        ("projection-scraper", ["--start-year", "2019"]),
    ]


def test_schedule_is_unchanged(instance):
    jobs = {(job.job_func.__name__, str(job.start_day), str(job.at_time)) for job in schedule.get_jobs()}
    assert ("run_salary_scraper", "tuesday", "09:00:00") in jobs
    assert ("run_backfill", "tuesday", "09:30:00") in jobs
    assert ("run_backup", "None", "03:00:00") in jobs
    projection_runs = [job for job in jobs if job[0] == "run_projection_scraper"]
    assert len(projection_runs) == 3 * 11  # hourly 10:00-20:00, Tue-Thu
