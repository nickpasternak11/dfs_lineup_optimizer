export DOCKER_BUILDKIT=1

COMPOSE_BUILD_FILE := docker-compose.build.yml
COMPOSE_RUN_FILE := docker-compose.run.yml
NETWORK := dfs_optimizer_network
DATA_VOLUME := /dfs_data:/app/data

.PHONY: down build run run-salary-scraper run-projection-scraper clean

down:
	docker compose -f $(COMPOSE_RUN_FILE) down

build:
	docker compose -f $(COMPOSE_BUILD_FILE) build --parallel

run: down
	docker compose -f $(COMPOSE_RUN_FILE) up -d

run-salary-scraper: down
	docker compose -f $(COMPOSE_RUN_FILE) up -d selenium-web-driver
	docker run --rm -v $(DATA_VOLUME) --network $(NETWORK) dfs-salary-scraper
	docker compose -f $(COMPOSE_RUN_FILE) down selenium-web-driver

run-projection-scraper: down
	docker run --rm -v $(DATA_VOLUME) dfs-projection-scraper
