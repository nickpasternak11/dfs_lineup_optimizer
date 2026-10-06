export DOCKER_BUILDKIT=1

COMPOSE_BUILD_FILE := docker-compose.build.yml
COMPOSE_RUN_FILE := docker-compose.run.yml
DATA_VOLUME := /dfs_data:/app/data
NETWORK := dfs_optimizer_network
ENV_FILE := .env
BACKUP_DIR ?= /dfs_backups

# One-off scraper containers need the app network and DB credentials; the
# orchestrator supplies the same when it launches them on a schedule.
DOCKER_RUN := docker run --rm \
	--network $(NETWORK) \
	--env-file $(ENV_FILE) \
	-e POSTGRES_HOST=dfs-postgres \
	-e POSTGRES_PORT=5432

# Migration tooling additionally needs the CSV data mount.
MIGRATION_RUN := $(DOCKER_RUN) -v $(DATA_VOLUME)

.PHONY: down build run run-salary-scraper run-projection-scraper run-game-log-loader \
	backfill backfill-game-logs predict-model backtest-model backtest-props normalize-names psql \
	migrate migrate-dry-run verify-migration \
	db-upgrade db-downgrade db-stamp db-revision db-history db-current \
	backup list-backups restore \
	test test-api test-salary-scraper test-projection-scraper test-game-log-loader \
	test-orchestrator test-projection-model test-frontend test-db \
	load-test

down:
	docker compose -f $(COMPOSE_RUN_FILE) down

build:
	docker compose -f $(COMPOSE_BUILD_FILE) build --parallel

run: down
	docker compose -f $(COMPOSE_RUN_FILE) up -d

# Plain targets scrape the current week, matching the orchestrator's schedule.
# Pass ARGS for other targets, e.g. ARGS="--year 2024 --week 5" (projections).
# The salary source only serves the current NFL week, so it takes no --week;
# past seasons' salaries can only be collected during that week of the year.
run-salary-scraper:
	$(DOCKER_RUN) dfs-salary-scraper $(ARGS)

run-projection-scraper:
	$(DOCKER_RUN) dfs-projection-scraper $(ARGS)

# nflverse games and game logs for the current season (ARGS="--year 2024" for
# another). The orchestrator runs this daily at 6:00 AM ET in season.
run-game-log-loader:
	$(DOCKER_RUN) dfs-game-log-loader $(ARGS)

# Tests run in each service's `test` build stage, with the same dependencies as
# the deployed image. No database, network or running stack needed (test-db
# starts its own throwaway Postgres).
test: test-api test-salary-scraper test-projection-scraper test-game-log-loader test-orchestrator \
	test-projection-model test-frontend test-db

test-api:
	docker build -q --target test -f api/Dockerfile -t dfs-api-test . >/dev/null
	docker run --rm dfs-api-test

test-salary-scraper:
	docker build -q --target test -f system/salary-scraper/Dockerfile -t dfs-salary-scraper-test . >/dev/null
	docker run --rm dfs-salary-scraper-test

test-projection-scraper:
	docker build -q --target test -f system/projection-scraper/Dockerfile -t dfs-projection-scraper-test . >/dev/null
	docker run --rm dfs-projection-scraper-test

test-game-log-loader:
	docker build -q --target test -f system/game-log-loader/Dockerfile -t dfs-game-log-loader-test . >/dev/null
	docker run --rm dfs-game-log-loader-test

test-projection-model:
	docker build -q --target test -f system/projection-model/Dockerfile -t dfs-projection-model-test . >/dev/null
	docker run --rm dfs-projection-model-test

test-orchestrator:
	docker build -q --target test -f system/orchestrator/Dockerfile -t dfs-orchestration-test . >/dev/null
	docker run --rm dfs-orchestration-test

test-frontend:
	docker build -q --target test -t dfs-frontend-test frontend >/dev/null
	docker run --rm dfs-frontend-test

# Fails if shared/dfs_db/models.py and the Alembic migrations have drifted
# apart (see the `test` stage in db/Dockerfile). Runs against a throwaway
# Postgres on its own network, named per run and removed on exit either way,
# so it never touches dfs-postgres, its volume or dfs_optimizer_network.
test-db:
	docker build -q --target test -f db/Dockerfile -t dfs-db-migrate-test . >/dev/null
	@set -e; name=dfs-db-test-$$$$; \
	trap 'docker rm -f $$name >/dev/null 2>&1; docker network rm $$name >/dev/null 2>&1' EXIT; \
	trap 'exit 130' INT TERM; \
	docker network create $$name >/dev/null; \
	docker run -d --rm --name $$name --network $$name -e POSTGRES_USER=dfs \
		-e POSTGRES_DB=dfs -e POSTGRES_PASSWORD=test postgres:16-alpine >/dev/null; \
	i=0; until docker exec $$name pg_isready -q -h 127.0.0.1 -U dfs; do \
		i=$$((i + 1)); [ $$i -lt 60 ] || { echo 'test-db: Postgres did not start'; exit 1; }; \
		sleep 1; \
	done; \
	docker run --rm --network $$name -e POSTGRES_HOST=$$name -e POSTGRES_PASSWORD=test \
		dfs-db-migrate-test

# Read-only load test against a running API (see api/loadtest/README.md).
# Defaults to the stack's dfs-api; point LOAD_TEST_URL at another container on
# the network to compare builds, and pass ARGS such as "--concurrency 1 5 --duration 10".
LOAD_TEST_URL ?= http://dfs-api:8080
load-test:
	docker run --rm --network $(NETWORK) -v $(CURDIR)/api/loadtest:/loadtest:ro python:3.10-slim \
		sh -c 'pip install -q --disable-pip-version-check --root-user-action=ignore \
			-r /loadtest/requirements.txt && python /loadtest/loadtest.py --base-url $(LOAD_TEST_URL) $(ARGS)'

# The orchestrator's Tuesday 9:30 AM ET job: this week of every season from
# BACKFILL_START_YEAR through last season. Safe to re-run.
BACKFILL_START_YEAR ?= 2018
backfill:
	$(DOCKER_RUN) dfs-salary-scraper --start-year $(BACKFILL_START_YEAR)
	$(DOCKER_RUN) dfs-projection-scraper --start-year $(BACKFILL_START_YEAR)

# Every season of nflverse game logs from GAME_LOG_START_YEAR through this one.
# Earlier than the scrapers' history: the projection model trains on these
# seasons. Each season is one download, so this takes under a minute. Safe
# to re-run.
GAME_LOG_START_YEAR ?= 2012
backfill-game-logs:
	$(DOCKER_RUN) dfs-game-log-loader --start-year $(GAME_LOG_START_YEAR)

# Our model's projections for this week's games still to come, stored as a
# snapshot in model_projections (the orchestrator runs it every morning).
# ARGS="--dry-run" prints them instead.
predict-model:
	$(DOCKER_RUN) dfs-projection-model predict $(ARGS)

# The projection model's walk-forward backtest (#44): trains on each season's
# earlier seasons and scores it against FantasyPros on the accuracy page's
# rows. Reads the database, writes nothing; about a minute.
backtest-model:
	$(DOCKER_RUN) dfs-projection-model backtest $(ARGS)

# Projections from sportsbook player props (#50) against FantasyPros and the
# model, on the season an Odds API export covers. Fits on the first half of
# its weeks, scores the second.
PROPS_DIR ?= /dfs_data/props
backtest-props:
	$(DOCKER_RUN) -v $(PROPS_DIR):/props:ro dfs-projection-model props $(ARGS)

# One-time: rename players stored under other spellings (legacy CSVs, the
# salary page) to FantasyPros' rankings spelling. Safe to re-run; preview with
# ARGS=--dry-run. The scrapers keep each new week consistent on their own.
normalize-names:
	$(DOCKER_RUN) dfs-db-migrate python -m dfs_db.normalize $(ARGS)

psql:
	docker compose -f $(COMPOSE_RUN_FILE) exec dfs-postgres \
		psql -U $${POSTGRES_USER:-dfs} -d $${POSTGRES_DB:-dfs}

# Database backups. The orchestrator also runs one nightly at 3:00 AM ET.
backup:
	docker compose -f $(COMPOSE_RUN_FILE) exec dfs-orchestration python -m src.backup

list-backups:
	ls -lht $(BACKUP_DIR)

# Destructive: replaces the database's contents with FILE. Stops the API and
# orchestrator for the duration so nothing reads or writes mid-restore.
# Usage: make restore FILE=dfs_20260926T070000Z.dump
restore:
	@test -n "$(FILE)" || (echo 'Usage: make restore FILE=<name from make list-backups>' && exit 1)
	docker compose -f $(COMPOSE_RUN_FILE) stop dfs-api dfs-orchestration
	docker run --rm --network $(NETWORK) --env-file $(ENV_FILE) \
		-v $(BACKUP_DIR):/backups:ro -e FILE=$(FILE) postgres:16-alpine \
		sh -c 'PGPASSWORD="$$POSTGRES_PASSWORD" pg_restore -h dfs-postgres \
			-U "$${POSTGRES_USER:-dfs}" -d "$${POSTGRES_DB:-dfs}" \
			--clean --if-exists --no-owner "/backups/$$FILE"'
	docker compose -f $(COMPOSE_RUN_FILE) start dfs-api dfs-orchestration

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
