import os
import time

import backoff
import docker
import schedule
from src.backup import run_backup
from src.configs import log

# Forwarded to scraper containers so they reach the same database as the API.
DB_ENV_VARS = (
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
)

# First season the weekly backfill collects; it runs through last season.
BACKFILL_START_YEAR = os.getenv("BACKFILL_START_YEAR", "2018")


class ScraperOrchestrator:
    def __init__(self):
        # Docker client
        self.docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        self.network_name = "dfs_optimizer_network"
        # Set up schedules
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
                schedule.every().__getattribute__(day).at(
                    f"{hour:02d}:00", "America/New_York"
                ).do(self.run_projection_scraper)
        # Database backup → Daily, 3:00 AM ET
        schedule.every().day.at("03:00", "America/New_York").do(self.run_backup)
        log.info("✅ Schedules set up successfully")

    def run_backup(self):
        # schedule re-raises job exceptions out of run_pending(), which would
        # stop the scheduler loop; a failed backup must only be logged.
        try:
            run_backup(self.docker_client)
        except Exception as e:  # noqa: BLE001
            log.error(f"Database backup failed: {e!s}")

    @backoff.on_exception(backoff.expo, docker.errors.APIError, max_tries=3)
    def run_salary_scraper(self):
        log.info("Starting scheduled salary scraper...")
        self.run_container("dfs-salary-scraper")

    @backoff.on_exception(backoff.expo, docker.errors.APIError, max_tries=3)
    def run_projection_scraper(self):
        log.info("Starting scheduled projection scraper...")
        self.run_container("dfs-projection-scraper")

    def run_backfill(self):
        log.info(
            "Starting scheduled backfill of this week for %s through last season...",
            BACKFILL_START_YEAR,
        )
        args = ["--start-year", BACKFILL_START_YEAR]
        self.run_container("dfs-salary-scraper", command=args)
        self.run_container("dfs-projection-scraper", command=args)

    def run_container(self, container_name: str, command: list[str] | None = None):
        container_config = {
            "image": container_name,
            # Appended to the image's `python main.py` entrypoint.
            "command": command,
            "detach": True,
            "network": self.network_name,
            "labels": {"logging": "promtail"},
            "environment": {
                name: os.environ[name]
                for name in DB_ENV_VARS
                if name in os.environ
            },
            "name": container_name,
            "auto_remove": True,
        }

        try:
            container = self.docker_client.containers.run(**container_config)

            # Stream logs while running
            for line in container.logs(stream=True):
                log.info(f"[{container_name}] {line.decode().strip()}")

            # Capture exit status
            exit_code = container.wait()["StatusCode"]
            if exit_code == 0:
                log.info(f"{container_name} completed successfully.")
            else:
                log.error(f"{container_name} exited with status code {exit_code}")

        except docker.errors.APIError as e:
            log.error(f"Docker API error running {container_name}: {e!s}")
        except Exception as e:
            log.error(f"Error running {container_name}: {e!s}")

    def run(self):
        log.info("Starting scheduler loop...")
        while True:
            schedule.run_pending()
            time.sleep(30)
