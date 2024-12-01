import time

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
        log.info("Setting up schedules")
        # Salary scraper schedule
        schedule.every().tuesday.at("09:00", "America/New_York").do(self.run_salary_scraper)
        # Projection scraper schedule
        for day in ["tuesday", "wednesday", "thursday", "friday", "saturday"]:
            for time in ["09:30", "12:00", "14:30", "17:00", "19:30"]:
                schedule.every().__getattribute__(day).at(time, "America/New_York").do(self.run_projection_scraper)

    def run_salary_scraper(self):
        self.run_container("salary-scraper")

    def run_projection_scraper(self):
        self.run_container("projection-scraper")

    def run_container(self, container_name):
        try:
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
            container = self.docker_client.containers.run(**container_config)
            log.info(f"Running container: {container.name}")
        except docker.errors.APIError as e:
            log.error(f"Error starting {container_name} container: {str(e)}")

    def run(self):
        while True:
            schedule.run_pending()
            log.info("Checking schedules")
            time.sleep(60)  # Check every minute


if __name__ == "__main__":
    log.info("Starting orchestrator")
    orchestrator = ScraperOrchestrator()
    orchestrator.run()
