# DFS Lineup Optimizer

A full-stack application for optimizing DraftKings NFL daily fantasy sports (DFS) lineups using web scraping and mathematical optimization.

## Overview

![WebApp](media/dfs_optimizer_img.png)

This project combines automated data collection with lineup optimization to generate DraftKings NFL DFS lineups. It consists of Dockerized scraper services, a FastAPI backend, a React frontend, and a PostgreSQL database that all services share.

### Key Features

- **Automated Data Collection**: Salary and projection scrapers for DraftKings and FantasyPros data
- **Historical Backfill**: Scrapers can collect past seasons' data for the current week
- **Lineup Optimization**: Generates multiple lineups using salary, position, projection, and player constraints
- **Web Interface**: Filterable player pool with include/exclude actions and suggested lineup results
- **Containerized**: Docker Compose build and runtime configurations for the application and data services

## Architecture

```
dfs_lineup_optimizer/
├── api/                              # FastAPI service
│   ├── main.py                       # Uvicorn entrypoint
│   ├── app/
│   │   ├── routes/                   # Projection and optimization endpoints
│   │   ├── db/                       # Player pool loading and lineup optimization
│   │   ├── models/                   # Request and response models
│   │   └── configs/                  # API configuration
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                         # React web application
├── system/
│   ├── orchestrator/                 # Scraper scheduling service
│   ├── salary-scraper/               # DraftKings salary scraper
│   └── projection-scraper/           # FantasyPros projection scraper
├── shared/dfs_db/                    # Shared DB config, sessions, ORM models, writes
├── db/                               # Schema migrations (Alembic)
│   └── migrations/versions/          # One file per schema change
├── migration/                        # One-time CSV → PostgreSQL data load
├── data/                             # Legacy CSV salaries and projections
├── docker-compose.build.yml          # Image build definitions
├── docker-compose.run.yml            # Runtime services, ports and volumes
├── .env.example                      # Database credentials template
├── Makefile                          # Build, run, scraper and database shortcuts
└── README.md
```

### Runtime Services

The runtime Compose configuration starts:

- `dfs-postgres`: PostgreSQL 16, data in the `dfs_postgres_data` Docker volume, port `5432` on `127.0.0.1` only
- `dfs-frontend`: React application served on port `3000`
- `dfs-api`: FastAPI application served on port `8080`
- `dfs-orchestration`: scraper scheduling service

The scrapers, schema tool (`dfs-db-migrate`) and CSV loader (`dfs-migration`) are one-off images, run by the orchestrator or by `make`. All services share the `dfs_optimizer_network` network.

## Getting Started

### Prerequisites

- **Docker** ([Install](https://docs.docker.com/get-docker/))
- **Docker Compose** (included with Docker Desktop)
- **Make** (optional, for convenient commands)
  - macOS: `xcode-select --install`
  - Ubuntu: `sudo apt-get install make`
  - Windows: `choco install make`

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/nickpasternak11/dfs_lineup_optimizer.git
cd dfs_lineup_optimizer
```

2. Create `.env` and set a real `POSTGRES_PASSWORD`. `.env` is git-ignored; never commit it.
```bash
cp .env.example .env
```

3. Build and start all services, then create the database schema:
```bash
make build
make run
make db-upgrade
```

4. Load data, either by scraping the current week or by importing the legacy CSVs (see [Migrating from CSV](#migrating-from-csv)):
```bash
make run-salary-scraper
make run-projection-scraper
```

5. Access the application at http://localhost:3000

The frontend loads the current season and week from the API, displays the available player pool, and submits optimization requests to the API. The API is available at http://localhost:8080.

## Usage

### Running Scrapers

With no arguments, each scraper collects the current week, the same as the orchestrator's schedule:

```bash
make run-salary-scraper
make run-projection-scraper
```

The stack must be running (`make run`), since the scrapers write to `dfs-postgres`.

Scheduled runs (orchestrator):
- **Salary scraper**: Tuesdays at 9:00 AM ET
- **Past-season backfill**: Tuesdays at 9:30 AM ET (see below)
- **Projection scraper**: hourly, 10:00 AM–8:00 PM ET, Tuesday through Thursday
- **Database backup**: daily at 3:00 AM ET

### Backfilling Past Seasons

Both scrapers can collect past seasons, with one constraint: **the salary source only serves the current NFL week**. It accepts any season, but you can only collect past seasons' salaries for the week the live season is currently in. So during week N of the live season, you backfill week N of every past season.

**This runs automatically.** Every Tuesday at 9:30 AM ET the orchestrator backfills the current week for every season from 2018 through last season, so during 2026 week 3 it collects week 3 of 2018–2025. The history fills in one week at a time over the season. Set `BACKFILL_START_YEAR` in `.env` to change the first season.

To run it by hand, e.g. if the stack was down on Tuesday, run it before the next week starts:

```bash
make backfill
```

Or with explicit options: `--start-year` alone covers through last season, and the projection scraper's `--week` defaults to the current week:

```bash
make run-salary-scraper     ARGS="--start-year 2018"
make run-projection-scraper ARGS="--start-year 2018 --end-year 2020 --week 5"
```

A projection-only backfill works for any week at any time. Salaries don't.

What backfilled weeks contain:

| Field | Past seasons |
|-------|--------------|
| Rankings, grades, projected and average FPTS | Real, week-specific |
| Injury status and type | Real, week-specific |
| Salary, opponent, home/away | Real, for the current week number only |
| Kickoff | `NULL`: the source only gives a weekday and time |

Each scraper run replaces that week's rows entirely, so re-running a week is safe and removes stale or renamed players. A week appears in the player pool only once both scrapers have written it.

Scrapers refuse to save a partial scrape. A run fails without writing anything if:
- a page errors after 3 retries,
- any position's rankings come back empty,
- the current week can't be determined, or
- the new scrape has under 80% of the rows already stored for that week.

The last check exists because a changed page layout can return plausible-looking but incomplete data. If a week legitimately shrank, override it with `--allow-shrink`, e.g. `ARGS="--year 2025 --week 3 --allow-shrink"`. In a `--start-year` backfill, a failing season is logged and skipped, and the run exits non-zero.

Other scraper options: `--year` and (projections only) `--week` scrape a single target, e.g. `ARGS="--year 2024 --week 5"`.

### Generate Lineups in the Web App

Use the settings panel to choose the year, week, defense, and optional one-tight-end constraint, then select **Optimize lineups**. The player pool supports:

- Search by player name
- Filtering by position, team, and opponent
- Include and exclude actions for player constraints
- Rank, grade, average FPTS, projected FPTS, and salary columns

The suggested lineups panel displays multiple optimized results with player, position, team, opponent, projected FPTS, salary, and include/exclude actions.

The API endpoints used by the frontend are:

- `GET /projections/current_year`
- `GET /projections/current_week`
- `POST /projections`
- `POST /optimize`

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React, JavaScript, CSS, HTML | Interactive UI for lineup management |
| **Backend** | Python, FastAPI, Pandas, PuLP | API and optimization engine |
| **Database** | PostgreSQL, SQLAlchemy, Alembic | Storage, data access and schema migrations |
| **Scraping** | Requests, BeautifulSoup, Pandas | Salary and projection collection |
| **Orchestration** | Docker, Docker Compose, schedule | Container management and task scheduling |

## Key Components

### Orchestrator
Runs the scraper schedule in its own container. It uses the Docker socket to launch scraper containers on the app network and passes them the database credentials.

### Salary Scraper
Collects DraftKings salaries, opponents, home/away and kickoff times from the FantasyPros DraftKings salary-changes page, and writes them to `player_salaries`.

### Projection Scraper
Collects FantasyPros weekly rankings, expert grades, projected points, trailing four-week average points and injury reports for QB, RB, WR, TE and DST, and writes them to `player_projections`.

### API and Lineup Optimizer
The FastAPI service reads each week's player pool from PostgreSQL and exposes the projection and optimization endpoints. Its optimization engine constructs valid lineups within DraftKings constraints.

**Optimization approach:**
- Maximizes projected fantasy points
- Respects salary cap
- Enforces position limits
- Excludes players whose games have already kicked off (unless requested)

## Data Storage

All data lives in PostgreSQL (database `dfs`), in the `dfs_postgres_data` Docker volume.

| Object | Written by | Contents |
|--------|-----------|----------|
| `player_salaries` | Salary scraper | Salary, salary change, team, opponent, home/away, kickoff |
| `player_projections` | Projection scraper | Rank, grade, projected and average FPTS, injury status |
| `weekly_player_pool` (view) | — | Joins the two per `(year, week, player)` and derives `value`; this is what the API reads |

Both tables are keyed on `(year, week, player)`. Columns that older data predates (`home`, `kickoff`, `salary_change`, `injury_status`, `injury_type`) are nullable.

To inspect the data:
```bash
make psql
```

The volume survives `make down` and restarts. **`docker compose -f docker-compose.run.yml down -v` or `docker volume rm dfs_postgres_data` deletes all data**, and anything scraped since the CSV migration exists nowhere else. Keep backups (below).

### Backups

The orchestrator runs `pg_dump` every night at 3:00 AM ET and writes the result to `/dfs_backups` on the host. That directory is outside the Docker volume, so `down -v` doesn't touch it. It keeps the newest 14 dumps. A failed dump never deletes older ones.

```bash
make backup                                    # take a backup now
make list-backups                              # newest first
make restore FILE=dfs_20260926T070000Z.dump    # replace the database with a backup
```

`make restore` is destructive: it drops and recreates every table from the dump. It stops the API and orchestrator while it runs and starts them again afterwards. Change the location or retention with `BACKUP_DIR` and `BACKUP_RETENTION` in `.env`.

`/dfs_backups` is on the same machine as the database, so it protects against deleted volumes and bad writes, not a lost disk. Copy it somewhere else periodically for that.

### Schema Migrations

The schema is managed by Alembic in `db/migrations/`. The ORM models in `shared/dfs_db/models.py` must match it.

```bash
make db-upgrade                        # apply pending migrations
make db-downgrade                      # roll back one migration (or REV=<id>)
make db-current                        # show the applied revision
make db-history                        # list all revisions
make db-revision MSG="add some column" # autogenerate a migration from model changes
```

After editing `models.py`, generate a revision, review the generated file in `db/migrations/versions/`, then run `make db-upgrade`. The `weekly_player_pool` view is not ORM-mapped, so changes to it must be written into a migration by hand.

## Migrating from CSV

Before the PostgreSQL migration, data was stored as CSV files in `/dfs_data/salaries/dk_salary_YYYY_wW.csv` and `/dfs_data/projections/fp_projection_YYYY_wW.csv`. The `migration/` tool loads them into the database once. The CSVs are only read, never modified.

**Fresh database** (no schema yet):
```bash
make build
make run
make db-upgrade          # create the schema
make migrate-dry-run     # parse every CSV and report what would be written
make migrate             # write to PostgreSQL
make verify-migration    # compare every CSV against the database
```

**Database created before Alembic was added** (the schema already exists from the old `db/init` script): run `make db-stamp` once instead of `make db-upgrade`. It records the initial migration as applied without re-running it.

What the loader does:
- Takes year and week from the filename.
- **Skips files whose rows come from a different season than their filename.** Some legacy files were written by a buggy backfill that mixed the current season's rankings with past seasons' salaries. Override with `ARGS="--allow-year-mismatch"`.
- Nulls kickoffs that fall outside the season (August through February).
- Leaves columns missing from older files `NULL`.
- Upserts, so it is safe to re-run after a partial failure.

`make migrate` and `make migrate-dry-run` accept filters, e.g. `ARGS="--year 2025"` or `ARGS="--dataset salaries --year 2024 --week 3"`. `verify-migration` accepts `--year`, `--week` and `--show-missing`.

> **Do not re-run `make migrate` after the scrapers have written the same weeks.** The legacy CSVs spell some names differently (e.g. `Packers` vs `Green Bay Packers`), so the loader would add duplicate players to weeks the scrapers have since replaced.

## Development

### Docker and Make Commands

```bash
make build                    # build all images
make run                      # start the stack (stops it first)
make down                     # stop the stack
make psql                     # open a psql shell on the database
make backup                   # back up the database now (see Backups)

make run-salary-scraper       # scrape the current week (ARGS for other targets)
make run-projection-scraper
make backfill                 # this week of every past season (runs Tuesdays anyway)

make db-upgrade               # schema migrations (see Schema Migrations)
make migrate                  # CSV import (see Migrating from CSV)
```

To run the frontend locally outside Docker:

```bash
cd frontend
npm install
npm start
```

The legacy Create React App toolchain may require `NODE_OPTIONS=--openssl-legacy-provider` with newer Node versions.
