from configs import log
import docker
import schedule
import time
import datetime

class ScraperOrchestrator:
    def __init__(self):
        # Docker client
        self.docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        self.network_name = "dfs_optimizer_network"
        # Set up schedules
        self.setup_schedules()

    def setup_schedules(self):
        log.info("Setting up schedules")
        # Salary scraper schedule (every Tuesday at noon)
        schedule.every().tuesday.at("12:00", "America/New_York").do(self.run_salary_scraper)
        # Projection scraper schedule (Tuesday-Saturday at 13:00, 16:30, and 20:00)
        for day in ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
            for time in ["13:00", "16:30", "20:00"]:
                schedule.every().__getattribute__(day).at(time, "America/New_York").do(self.run_projection_scraper)

    def run_salary_scraper(self):
        log.info(f"Running salary scraper at {datetime.datetime.now()}")
        self.run_container("salary-scraper")

    def run_projection_scraper(self):
        log.info(f"Running projection scraper at {datetime.datetime.now()}")
        self.run_container("projection-scraper")

    def run_container(self, container_name):
        try:
            container_config = {
                'image': container_name,
                'detach': True,
                'network': self.network_name,
                'labels': {"logging": "promtail"},
                'volumes': {
                    "/dfs_data": {"bind": "/app/data", "mode": "rw"},
                },
                'name': container_name,
                "auto_remove": True
            }
            container = self.docker_client.containers.run(**container_config)
            log.info(f"Started container: {container.name}")
        except docker.errors.APIError as e:
            log.error(f"Error starting {container_name} container: {str(e)}")

    def run(self):
        log.info("Workers Orchestration started. Running scheduled tasks...")
        while True:
            schedule.run_pending()
            log.info(f"Checked schedule at {datetime.datetime.now()}")
            time.sleep(60)  # Check every minute


if __name__ == "__main__":
    log.info("Starting orchestrator..")
    orchestrator = ScraperOrchestrator()
    orchestrator.run()