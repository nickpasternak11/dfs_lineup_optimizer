import time
from zoneinfo import ZoneInfo

import backoff
import docker
import schedule
from configs import log


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
        # Projection scraper → Every hour, Tue 10:00 AM through Thu 8:00 PM ET
        for day in ["tuesday", "wednesday", "thursday"]:
            for hour in range(10, 21):  # 10:00 AM to 8:00 PM inclusive
                schedule.every().__getattribute__(day).at(
                    f"{hour:02d}:00", "America/New_York"
                ).do(self.run_projection_scraper)
        log.info("✅ Schedules set up successfully")

    @backoff.on_exception(backoff.expo, docker.errors.APIError, max_tries=3)
    def run_salary_scraper(self):
        log.info("Starting scheduled salary scraper...")
        self.run_container("dfs-salary-scraper")

    @backoff.on_exception(backoff.expo, docker.errors.APIError, max_tries=3)
    def run_projection_scraper(self):
        log.info("Starting scheduled projection scraper...")
        self.run_container("dfs-projection-scraper")

    def run_container(self, container_name: str):
        container_config = {
            "image": container_name,
            "detach": True,
            "network": self.network_name,
            "labels": {"logging": "promtail"},
            "volumes": {
                "/dfs_data": {"bind": "/app/data", "mode": "rw"},
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
            log.error(f"Docker API error running {container_name}: {str(e)}")
        except Exception as e:
            log.error(f"Error running {container_name}: {str(e)}")

    def run(self):
        log.info("Starting scheduler loop...")
        while True:
            schedule.run_pending()
            time.sleep(30)


if __name__ == "__main__":
    log.info("Starting orchestrator...")
    orchestrator = ScraperOrchestrator()
    orchestrator.run()
