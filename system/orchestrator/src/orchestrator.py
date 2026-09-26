import os
import subprocess
import sys
import time

import schedule
from src.backup import run_backup
from src.configs import log

# The scrapers' code is copied into the image here (see the Dockerfile) and
# each runs in its own child process -- no Docker socket needed.
JOBS_DIR = os.getenv("JOBS_DIR", "/app/jobs")

# First season the weekly backfill collects; it runs through last season.
BACKFILL_START_YEAR = os.getenv("BACKFILL_START_YEAR", "2018")


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
        # Database backup → Daily, 3:00 AM ET
        schedule.every().day.at("03:00", "America/New_York").do(self.run_backup)
        log.info("✅ Schedules set up successfully")

    def run_backup(self):
        # schedule re-raises job exceptions out of run_pending(), which would
        # stop the scheduler loop; a failed backup must only be logged.
        try:
            run_backup()
        except Exception as e:  # noqa: BLE001
            log.error(f"Database backup failed: {e!s}")

    def run_salary_scraper(self):
        log.info("Starting scheduled salary scraper...")
        self.run_scraper("salary-scraper")

    def run_projection_scraper(self):
        log.info("Starting scheduled projection scraper...")
        self.run_scraper("projection-scraper")

    def run_backfill(self):
        log.info(
            "Starting scheduled backfill of this week for %s through last season...",
            BACKFILL_START_YEAR,
        )
        args = ["--start-year", BACKFILL_START_YEAR]
        self.run_scraper("salary-scraper", args)
        self.run_scraper("projection-scraper", args)

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
            exit_code = process.wait()
        except OSError as e:
            log.error(f"Could not start {name}: {e!s}")
            return False

        if exit_code == 0:
            log.info(f"{name} completed successfully.")
            return True
        log.error(f"{name} exited with status code {exit_code}")
        return False

    def run(self):
        log.info("Starting scheduler loop...")
        while True:
            schedule.run_pending()
            time.sleep(30)
