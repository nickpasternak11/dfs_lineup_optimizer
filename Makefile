SALARY_SCRAPER_IMAGE_NAME = "salary-scraper"
LINEUP_OPTIMIZER_IMAGE_NAME = "lineup-optimizer"

build-salary-scraper:
	docker buildx build --target $(SALARY_SCRAPER_IMAGE_NAME) -t $(SALARY_SCRAPER_IMAGE_NAME) .

build-lineup-optimizer:
	docker buildx build --target $(LINEUP_OPTIMIZER_IMAGE_NAME) -t $(LINEUP_OPTIMIZER_IMAGE_NAME) .

run-salary-scraper: build-salary-scraper
	docker run --rm -v "./:/app" $(SALARY_SCRAPER_IMAGE_NAME)

run-lineup-optimizer: build-lineup-optimizer
	docker run --rm -v "./:/app" $(LINEUP_OPTIMIZER_IMAGE_NAME)