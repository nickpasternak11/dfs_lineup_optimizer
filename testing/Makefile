export DOCKER_BUILDKIT=1

SALARY_SCRAPER_IMAGE_NAME = "salary-scraper"
LINEUP_OPTIMIZER_IMAGE_NAME = "lineup-optimizer"
APP_IMAGE_NAME = "app"

build-salary-scraper:
	docker buildx build --target $(SALARY_SCRAPER_IMAGE_NAME) -t $(SALARY_SCRAPER_IMAGE_NAME) .

build-lineup-optimizer:
	docker buildx build --target $(LINEUP_OPTIMIZER_IMAGE_NAME) -t $(LINEUP_OPTIMIZER_IMAGE_NAME) .

run-salary-scraper: build-salary-scraper
	docker compose run --rm -v "/dfs_data:/app/data" $(SALARY_SCRAPER_IMAGE_NAME)

run-lineup-optimizer: build-lineup-optimizer
	docker compose run --rm -v "/dfs_data:/app/data" -e WEEK=$(WEEK) -e DST=$(DST) -e ONE_TE=$(ONE_TE) $(LINEUP_OPTIMIZER_IMAGE_NAME)

build-app:
	docker buildx build --target $(APP_IMAGE_NAME) -t $(APP_IMAGE_NAME) .

run-app: build-app
	docker compose run --rm -v "/dfs_data:/app/data" -p 5000:5000 -e FLASK_ENV=development -e FLASK_APP=src/app.py $(APP_IMAGE_NAME)
