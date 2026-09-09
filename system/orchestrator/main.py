from src.configs import log
from src.orchestrator import ScraperOrchestrator

if __name__ == "__main__":
    log.info("Starting orchestrator...")
    orchestrator = ScraperOrchestrator()
    orchestrator.run()
