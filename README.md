# DraftKings NFL DFS Lineup Optimizer

This repository contains a Python-based lineup optimizer for DraftKings NFL daily fantasy sports (DFS) contests. It scrapes salary data and projections, then uses optimization techniques to generate optimal lineups.

## Features

- Scrapes NFL DFS salary data from DraftDime
- Retrieves PPR projection data from FantasyPros  
- Optimizes lineups for DraftKings NFL contests
- Allows customization of optimization parameters
- Outputs optimal weekly lineups

## Installation

1. Clone the repository:

```bash
git clone https://github.com/username/dfs_lineup_optimizer.git
cd dfs_lineup_optimizer
```

2. Install Docker:

Docker is required to run the lineup optimizer. Follow the official Docker installation guide for your operating system:
- [Install Docker on Windows](https://docs.docker.com/desktop/install/windows-install/)
- [Install Docker on Mac](https://docs.docker.com/desktop/install/mac-install/)
- [Install Docker on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

3. Install Make:

Make is used to simplify the Docker commands. Installation instructions vary by operating system:
- Windows: Install [Chocolatey](https://chocolatey.org/install) and then run `choco install make`
- Mac: Make should be pre-installed. If not, install Xcode Command Line Tools with `xcode-select --install`
- Ubuntu: Run `sudo apt-get install make`

## Usage

### Salary Scraper

To gather the latest salary data:

```bash
make run-salary-scraper
```

### Lineup Optimizer

To run the lineup optimizer:

```bash
make run-lineup-optimizer [DST=<defense_team>]
```
By default, the optimizer will find the best value defense available.

## Customization

The lineup optimizer accepts several parameters:

- `YEAR`: NFL season year (default: current year)
- `WEEK`: Week number (default: current week) 
- `DST`: Desired defense (default: None)
- `USE_AVG_FPTS`: Use average fantasy points (default: false)
- `WEIGHTS`: Custom weighting for projections (JSON format)

## Project Structure

```
dfs-lineup-optimizer/
├── src/
|   ├── configs.py
|   ├── utils.py
│   ├── salary_scraper.py
│   └── lineup_optimizer.py
├── data/
│   ├── salaries/
│   └── lineups/
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
