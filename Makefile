export DOCKER_BUILDKIT=1

COMPOSE_BUILD_FILE := docker-compose.build.yml
COMPOSE_RUN_FILE := docker-compose.run.yml
DATA_VOLUME := /dfs_data:/app/data
NETWORK := dfs_optimizer_network
ENV_FILE := .env

# One-off scraper containers need the app network and DB credentials; the
# orchestrator supplies the same when it launches them on a schedule.
DOCKER_RUN := docker run --rm \
	--network $(NETWORK) \
	--env-file $(ENV_FILE) \
	-e POSTGRES_HOST=dfs-postgres \
	-e POSTGRES_PORT=5432

# Migration tooling additionally needs the CSV data mount.
MIGRATION_RUN := $(DOCKER_RUN) -v $(DATA_VOLUME)

.PHONY: down build run run-salary-scraper run-projection-scraper psql \
	migrate migrate-dry-run verify-migration \
	db-upgrade db-downgrade db-stamp db-revision db-history db-current

down:
	docker compose -f $(COMPOSE_RUN_FILE) down

build:
	docker compose -f $(COMPOSE_BUILD_FILE) build --parallel

run: down
	docker compose -f $(COMPOSE_RUN_FILE) up -d

# Plain targets scrape the current week, matching the orchestrator's schedule.
# Pass ARGS to backfill past seasons:
#   make run-projection-scraper ARGS="--start-year 2018 --end-year 2025 --week 3"
#   make run-salary-scraper     ARGS="--start-year 2018 --end-year 2025"
# The salary source only serves the current NFL week, so it takes no --week;
# past seasons' salaries can only be collected during that week of the year.
run-salary-scraper:
	$(DOCKER_RUN) dfs-salary-scraper $(ARGS)

run-projection-scraper:
	$(DOCKER_RUN) dfs-projection-scraper $(ARGS)

psql:
	docker compose -f $(COMPOSE_RUN_FILE) exec dfs-postgres \
		psql -U $${POSTGRES_USER:-dfs} -d $${POSTGRES_DB:-dfs}

# Load the existing /dfs_data CSVs into Postgres. Idempotent; pass filters with
# ARGS, e.g. `make migrate ARGS="--year 2025"`.
migrate:
	$(MIGRATION_RUN) dfs-migration python migrate_csv_to_postgres.py $(ARGS)

migrate-dry-run:
	$(MIGRATION_RUN) dfs-migration python migrate_csv_to_postgres.py --dry-run $(ARGS)

verify-migration:
	$(MIGRATION_RUN) dfs-migration python verify_migration.py $(ARGS)

# Schema migrations (Alembic, in db/). Requires dfs-postgres to already be
# running (`make run`), since the network is created by the compose stack.
db-upgrade:
	$(DOCKER_RUN) dfs-db-migrate alembic upgrade $(or $(REV),head)

db-downgrade:
	$(DOCKER_RUN) dfs-db-migrate alembic downgrade $(or $(REV),-1)

# One-time only: if your database already has the schema from before Alembic
# existed (the old db/init/001_schema.sql), run this instead of db-upgrade so
# revision 0001 is recorded as applied without re-running its DDL.
db-stamp:
	$(DOCKER_RUN) dfs-db-migrate alembic stamp head

db-history:
	$(DOCKER_RUN) dfs-db-migrate alembic history

db-current:
	$(DOCKER_RUN) dfs-db-migrate alembic current

# Autogenerate a new revision from model changes in shared/dfs_db/models.py.
# Usage: make db-revision MSG="add player headshot url"
db-revision:
	$(DOCKER_RUN) -v $(CURDIR)/db/migrations/versions:/app/db/migrations/versions \
		dfs-db-migrate alembic revision --autogenerate -m "$(MSG)"
