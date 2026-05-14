# DFS Lineup Optimizer

A full-stack application for optimizing DraftKings NFL daily fantasy sports (DFS) lineups using web scraping and mathematical optimization.

## Overview

This project combines automated data collection with intelligent lineup optimization to generate competitive DFS lineups for DraftKings NFL contests. It consists of multiple microservices orchestrated with Docker, a Python backend, and a React frontend.

### Key Features

- **Automated Data Collection**: Scheduled scrapers for salary data and player projections
- **Resilient Architecture**: Automatic retry logic with exponential backoff for API failures
- **Real-time Optimization**: Generates optimal lineups based on current player projections and salary constraints
- **Web Interface**: Interactive React dashboard for lineup management
- **Containerized**: Full Docker support for seamless deployment

## Architecture

```
dfs_lineup_optimizer/
├── system/                           # Microservices
│   ├── orchestrator/                 # Scheduler & container orchestration
│   │   ├── src/
│   │   │   └── main.py              # Handles scraper scheduling & retry logic
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── salary-scraper/              # DraftKings salary data scraper
│   │   ├── src/
│   │   │   ├── main.py              # Selenium-based salary scraper
│   │   │   └── utils.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── projection-scraper/          # FantasyPros projections scraper
│       ├── src/
│       │   ├── main.py              # Web scraper for player projections
│       │   ├── configs.py           # Column mappings & logging config
│       │   └── utils.py             # Data fetching & parsing utilities
│       ├── Dockerfile
│       └── requirements.txt
│
├── app/                              # Backend (Python)
│   ├── src/
│   │   ├── lineup_optimizer.py      # Optimization engine
│   │   ├── configs.py               # Configuration
│   │   └── utils.py                 # Helper functions
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                         # Frontend (React)
│   ├── src/
│   ├── public/
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml               # Service orchestration
├── Makefile                         # Build & run commands
└── README.md
```

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

2. Build and start all services:
```bash
make build
make up
```

3. Access the application at http://localhost:3000

## Usage

### Running Scrapers

**Collect salary data and projections:**
```bash
make run-salary-scraper
make run-projection-scraper
```

**Automatic scheduling** (via orchestrator):
```bash
make run-orchestrator
```

The orchestrator automatically runs:
- **Salary Scraper**: Every Tuesday at 9:00 AM ET
- **Projection Scraper**: Hourly from 10:00 AM to 8:00 PM ET (Tue-Thu)

### Generate Lineups

```bash
make run-lineup-optimizer WEEK=<week_number> [DST=<team_abbreviation>]
```

**Example:**
```bash
make run-lineup-optimizer WEEK=5 DST=KC
```

**Parameters:**
- `WEEK`: NFL week number (default: current week)
- `YEAR`: NFL season (default: current year)
- `DST`: Specific defense team (optional; auto-selects best value if omitted)

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React, JavaScript, CSS, HTML | Interactive UI for lineup management |
| **Backend** | Python, Pandas, NumPy | Data processing & optimization engine |
| **Scraping** | BeautifulSoup, Selenium, Requests | Web scraping for salary & projection data |
| **Orchestration** | Docker, Docker Compose, APScheduler | Container management & task scheduling |
| **Deployment** | Docker | Containerized microservices |

## Key Components

### Orchestrator
Manages scheduled tasks with automatic retry logic. Runs salary and projection scrapers on a predefined schedule and monitors container health.

**Features:**
- Exponential backoff retry strategy (3 attempts max)
- Real-time container log streaming
- Error handling & logging

### Salary Scraper
Extracts player salary data from DraftKings using Selenium and Chromium.

**Supports multiple contest slates:**
- Thu-Mon, Fri-Mon, Sat-Mon, Sat-Sun

### Projection Scraper
Fetches player projections and historical stats from FantasyPros.

**Data collected:**
- Weekly projections by position (QB, RB, WR, TE, DST)
- Historical performance stats
- Expert consensus grades

### Lineup Optimizer
Mathematical optimization engine that constructs valid lineups within DraftKings constraints.

**Optimization approach:**
- Maximizes projected fantasy points
- Respects salary cap
- Enforces position limits
- Removes low-graded players

## Development

### Docker Commands

```bash
# Build all images
make build

# Start all services
make up

# View logs
make logs

# Stop services
make down

# Run individual services
make run-orchestrator
make run-salary-scraper
make run-projection-scraper
make run-lineup-optimizer
```

## Data Storage

- **Salary data**: `data/salaries/dk_salary_YYYY_wWW.csv`
- **Projections**: `data/projections/projections_YYYY_wWW.csv`
- **Lineups**: `data/lineups/lineups_YYYY_wWW.csv`

