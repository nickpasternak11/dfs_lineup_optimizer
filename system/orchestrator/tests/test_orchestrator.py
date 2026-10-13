import textwrap
from datetime import datetime

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


IN_SEASON = datetime(2026, 9, 30, 12, 0, tzinfo=orchestrator.EASTERN)  # a Wednesday


@pytest.fixture
def instance(monkeypatch):
    monkeypatch.setattr(orchestrator, "now_eastern", lambda: IN_SEASON)
    created = ScraperOrchestrator()
    yield created
    schedule.clear()


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(orchestrator, "send_alert", sent.append)
    return sent


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
    assert ("run_game_log_loader", "None", "06:00:00") in jobs
    assert ("run_projection_model", "None", "08:30:00") in jobs
    # Sunday late swap: FantasyPros' news, a model run, then the swap.
    assert {("run_projection_scraper", "sunday", "11:35:00"), ("run_projection_model", "sunday", "11:40:00"),
            ("run_late_swap", "sunday", "11:50:00")} <= jobs
    # Lineups: checked every 15 minutes for the week's first kickoff.
    checks = [job for job in schedule.get_jobs() if job.job_func.__name__ == "save_lineups_before_kickoff"]
    assert [(job.interval, job.unit) for job in checks] == [(15, "minutes")]
    assert not any(name == "run_lineup_snapshot" for name, *_ in jobs)
    projection_runs = [job for job in jobs if job[0] == "run_projection_scraper"]
    assert len(projection_runs) == 3 * 11 + 1  # hourly 10:00-20:00 Tue-Thu, and Sunday's


def test_failed_scraper_alerts_with_its_last_log_lines(instance, jobs_dir, alerts, monkeypatch):
    monkeypatch.setenv("FAKE_EXIT", "3")
    instance.run_scraper("fake-scraper", ["--start-year", "2018"])
    assert len(alerts) == 1
    assert "fake-scraper --start-year 2018 exited with status code 3" in alerts[0]
    assert "args: --start-year 2018" in alerts[0]


def test_successful_scraper_sends_no_alert(instance, jobs_dir, alerts):
    instance.run_scraper("fake-scraper")
    assert alerts == []


def test_failed_backup_alerts(instance, alerts, monkeypatch):
    def fail():
        raise RuntimeError("pg_dump failed: connection refused")

    monkeypatch.setattr(orchestrator, "run_backup", fail)
    instance.run_backup()
    assert "Database backup failed: pg_dump failed: connection refused" in alerts[0]


def test_scrapers_skip_the_off_season(instance, monkeypatch):
    calls = []
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: calls.append(name))
    monkeypatch.setattr(
        orchestrator, "now_eastern", lambda: datetime(2026, 5, 5, 9, 0, tzinfo=orchestrator.EASTERN)
    )
    instance.run_salary_scraper()
    instance.run_projection_scraper()
    instance.run_backfill()
    instance.run_game_log_loader()
    instance.run_projection_model()
    instance.run_lineup_snapshot()
    instance.run_late_swap()
    instance.save_lineups_before_kickoff()
    assert calls == []


def test_game_log_loader_runs_the_current_season(instance, monkeypatch):
    calls = []
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: calls.append((name, args)))
    instance.run_game_log_loader()
    assert calls == [("game-log-loader", None)]


@pytest.fixture
def catch_up_env(instance, monkeypatch):
    """Catch-up with a fake week lookup and a configurable set of gaps."""
    ran = []
    state = {"missing": []}
    monkeypatch.setattr(orchestrator, "get_current_week", lambda: 4)
    monkeypatch.setattr(orchestrator, "missing_jobs", lambda season, week: state["missing"])
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: ran.append((name, args)))
    return ran, state


def test_catch_up_runs_only_what_is_missing(instance, catch_up_env):
    ran, state = catch_up_env
    state["missing"] = ["projections", "backfill"]
    instance.catch_up()
    assert ran == [
        ("projection-scraper", None),
        ("salary-scraper", ["--start-year", orchestrator.BACKFILL_START_YEAR]),
        ("projection-scraper", ["--start-year", orchestrator.BACKFILL_START_YEAR]),
    ]


def test_catch_up_does_nothing_when_the_week_is_complete(instance, catch_up_env):
    ran, _ = catch_up_env
    instance.catch_up()
    assert ran == []


def test_catch_up_waits_for_tuesdays_scheduled_runs(instance, catch_up_env, monkeypatch):
    ran, state = catch_up_env
    state["missing"] = ["salaries"]
    tuesday_morning = datetime(2026, 9, 29, 9, 45, tzinfo=orchestrator.EASTERN)
    monkeypatch.setattr(orchestrator, "now_eastern", lambda: tuesday_morning)
    instance.catch_up()
    assert ran == []


def test_catch_up_check_failure_alerts(instance, catch_up_env, alerts, monkeypatch):
    def unreachable():
        raise RuntimeError("Could not find the current week")

    monkeypatch.setattr(orchestrator, "get_current_week", unreachable)
    instance.catch_up()
    assert "Catch-up check failed: Could not find the current week" in alerts[0]


def test_projection_model_predicts(instance, monkeypatch):
    calls = []
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: calls.append((name, args)))
    instance.run_projection_model()
    assert calls == [("projection-model", ["predict"])]


def test_lineup_snapshot_saves_lineups(instance, monkeypatch):
    calls = []
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: calls.append((name, args)))
    instance.run_lineup_snapshot()
    assert calls == [("projection-model", ["lineups", "--on-first-game-day"])]


def test_late_swap_re_optimizes_the_saved_lineups(instance, monkeypatch):
    calls = []
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: calls.append((name, args)))
    instance.run_late_swap()
    assert calls == [("projection-model", ["lineups", "--late-swap"])]



@pytest.fixture
def kickoff_env(instance, monkeypatch):
    """The pre-kickoff check with a fake due week."""
    ran = []
    state = {"due": None}
    monkeypatch.setattr(orchestrator, "due_week", lambda now: state["due"])
    monkeypatch.setattr(instance, "run_scraper", lambda name, args=None: ran.append((name, args)))
    return ran, state


def test_lineups_are_saved_on_fresh_projections_before_the_first_kickoff(instance, kickoff_env):
    ran, state = kickoff_env
    state["due"] = (2026, 5)
    instance.save_lineups_before_kickoff()
    assert ran == [
        ("projection-scraper", None),
        ("projection-model", ["predict"]),
        ("projection-model", ["lineups", "--on-first-game-day"]),
    ]


def test_nothing_runs_when_no_week_is_due(instance, kickoff_env):
    ran, _ = kickoff_env
    instance.save_lineups_before_kickoff()
    assert ran == []


def test_a_failed_pre_kickoff_check_runs_nothing(instance, kickoff_env, alerts, monkeypatch):
    ran, _ = kickoff_env

    def unreachable(now):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(orchestrator, "due_week", unreachable)
    instance.save_lineups_before_kickoff()
    assert ran == [] and alerts == []
