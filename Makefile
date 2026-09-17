export DOCKER_BUILDKIT=1

COMPOSE_BUILD_FILE := docker-compose.build.yml
COMPOSE_RUN_FILE := docker-compose.run.yml
DATA_VOLUME := /dfs_data:/app/data

.PHONY: down build run run-salary-scraper run-projection-scraper clean

down:
	docker compose -f $(COMPOSE_RUN_FILE) down

build:
	docker compose -f $(COMPOSE_BUILD_FILE) build --parallel

run: down
	docker compose -f $(COMPOSE_RUN_FILE) up -d

run-salary-scraper:
	docker run --rm -v $(DATA_VOLUME) dfs-salary-scraper

run-projection-scraper:
	docker run --rm -v $(DATA_VOLUME) dfs-projection-scraper
