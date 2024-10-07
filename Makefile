export DOCKER_BUILDKIT=1

SALARY_SCRAPER_IMAGE_NAME = "salary-scraper"
LINEUP_OPTIMIZER_IMAGE_NAME = "lineup-optimizer"
CURRENT_DIR := $(shell pwd)

build-salary-scraper:
	docker buildx build --target $(SALARY_SCRAPER_IMAGE_NAME) -t $(SALARY_SCRAPER_IMAGE_NAME) .

build-lineup-optimizer:
	docker buildx build --target $(LINEUP_OPTIMIZER_IMAGE_NAME) -t $(LINEUP_OPTIMIZER_IMAGE_NAME) .

run-salary-scraper: build-salary-scraper
	docker compose run --rm -v "$(CURRENT_DIR):/app" $(SALARY_SCRAPER_IMAGE_NAME)
	docker compose down

run-lineup-optimizer: build-lineup-optimizer
	docker run --rm -v "$(CURRENT_DIR):/app" -e WEEK=$(WEEK) -e DST=$(DST) $(LINEUP_OPTIMIZER_IMAGE_NAME)

run: run-salary-scraper run-lineup-optimizer
