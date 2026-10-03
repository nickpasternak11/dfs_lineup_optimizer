import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

import schedule
from dfs_common.alerts import send_alert
from dfs_common.fantasypros import get_current_week
from dfs_common.season import current_season_year
from src.backup import run_backup
from src.catch_up import catch_up_allowed, in_season, missing_jobs
from src.configs import log

EASTERN = ZoneInfo("America/New_York")

# The scrapers' code is copied into the image here (see the Dockerfile) and
# each runs in its own child process -- no Docker socket needed.
JOBS_DIR = os.getenv("JOBS_DIR", "/app/jobs")

# First season the weekly backfill collects; it runs through last season.
BACKFILL_START_YEAR = os.getenv("BACKFILL_START_YEAR", "2018")

# How much of a failed job's output goes into its alert.
ALERT_LOG_LINES = 15


def now_eastern() -> datetime:
    return datetime.now(EASTERN)


class ScraperOrchestrator:
    def __init__(self):
        self.setup_schedules()

    def setup_schedules(self):
        log.info("Setting up scraper schedules...")
        # Salary scraper → Once per week, Tuesday 9:00 AM ET
        schedule.every().tuesday.at("09:00", "America/New_York").do(
            self.run_salary_scraper
        )
        # Past-season backfill → Once per week, Tuesday 9:30 AM ET. The salary
        # source only serves the current week, so each past season's copy of
        # this week can only be collected now; after the 9:00 live scrape so
        # the new week is already live, and before the 10:00 projection runs.
        schedule.every().tuesday.at("09:30", "America/New_York").do(self.run_backfill)
        # Projection scraper → Every hour, Tue 10:00 AM through Thu 8:00 PM ET
        for day in ["tuesday", "wednesday", "thursday"]:
            for hour in range(10, 21):  # 10:00 AM to 8:00 PM inclusive
                getattr(schedule.every(), day).at(
                    f"{hour:02d}:00", "America/New_York"
                ).do(self.run_projection_scraper)
        # Missed-run catch-up → Daily at noon ET (and at startup, see run())
        schedule.every().day.at("12:00", "America/New_York").do(self.catch_up)
        # Database backup → Daily, 3:00 AM ET
        schedule.every().day.at("03:00", "America/New_York").do(self.run_backup)
        log.info("✅ Schedules set up successfully")

    def alert(self, message: str) -> None:
        log.error(message)
        send_alert(f"DFS orchestrator: {message}")

    def run_backup(self):
        # schedule re-raises job exceptions out of run_pending(), which would
        # stop the scheduler loop; a failed backup must only be reported.
        try:
            run_backup()
        except Exception as e:  # noqa: BLE001
            self.alert(f"Database backup failed: {e!s}")

    def run_salary_scraper(self):
        if self.skip_off_season("salary scraper"):
            return
        log.info("Starting scheduled salary scraper...")
        self.run_scraper("salary-scraper")

    def run_projection_scraper(self):
        if self.skip_off_season("projection scraper"):
            return
        log.info("Starting scheduled projection scraper...")
        self.run_scraper("projection-scraper")

    def run_backfill(self):
        if self.skip_off_season("backfill"):
            return
        log.info(
            "Starting scheduled backfill of this week for %s through last season...",
            BACKFILL_START_YEAR,
        )
        args = ["--start-year", BACKFILL_START_YEAR]
        self.run_scraper("salary-scraper", args)
        self.run_scraper("projection-scraper", args)

    def skip_off_season(self, job: str) -> bool:
        # Off-season there is no current week to scrape; running would only
        # fail and alert every week from March to August.
        if in_season(now_eastern()):
            return False
        log.info("Off-season: skipping the %s", job)
        return True

    def catch_up(self):
        """Run any of this week's scrapes that are missing from the database."""
        now = now_eastern()
        if not catch_up_allowed(now):
            log.info("Catch-up: not checking now (off-season, Monday or early Tuesday)")
            return
        try:
            week = get_current_week()
            season = current_season_year(now.date())
            missing = missing_jobs(season, week)
        except Exception as e:  # noqa: BLE001
            self.alert(f"Catch-up check failed: {e!s}")
            return

        if not missing:
            log.info("Catch-up: %s week %s is complete", season, week)
            return
        log.warning("Catch-up: %s week %s is missing %s", season, week, ", ".join(missing))
        if "salaries" in missing:
            self.run_scraper("salary-scraper")
        if "projections" in missing:
            self.run_scraper("projection-scraper")
        if "backfill" in missing:
            self.run_backfill()

    def run_scraper(self, name: str, args: list[str] | None = None) -> bool:
        """Run a scraper's main.py in a child process, streaming its log.

        Returns True if it exited cleanly. Never raises: a failed job must not
        stop the scheduler loop.
        """
        workdir = os.path.join(JOBS_DIR, name)
        # Each scraper, and the orchestrator itself, has a top-level `src`
        # package, so the child must see only its own directory.
        env = {**os.environ, "PYTHONPATH": f"{workdir}:/app/shared"}
        command = [sys.executable, "main.py", *(args or [])]
        label = " ".join([name, *(args or [])])
        tail = deque(maxlen=ALERT_LOG_LINES)

        try:
            process = subprocess.Popen(
                command,
                cwd=workdir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                log.info(f"[{name}] {line.rstrip()}")
                tail.append(line.rstrip())
            exit_code = process.wait()
        except OSError as e:
            self.alert(f"Could not start {label}: {e!s}")
            return False

        if exit_code == 0:
            log.info(f"{name} completed successfully.")
            return True
        output = "\n".join(tail)
        self.alert(f"{label} exited with status code {exit_code}\n```\n{output}\n```")
        return False

    def run(self):
        # Catch up first: anything missed while the stack was down.
        self.catch_up()
        log.info("Starting scheduler loop...")
        while True:
            schedule.run_pending()
            time.sleep(30)
