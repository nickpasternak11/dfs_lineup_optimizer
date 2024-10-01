# DraftKings NFL DFS Lineup Optimizer

This repository contains a Python-based lineup optimizer for DraftKings NFL daily fantasy sports (DFS) contests. It scrapes salary data and projections, then uses optimization techniques to generate optimal lineups.

## Features

- Scrapes NFL DFS salary data from DraftDime
- Retrieves PPR projection data from FantasyPros  
- Optimizes lineups for DraftKings NFL contests
- Allows customization of optimization parameters
- Outputs optimal weekly lineups

## Installation

```bash
git clone https://github.com/username/dfs_lineup_optimizer.git
cd dfs_lineup_optimizer
pip install -r requirements.txt
```

## Usage

### Salary Scraper (Local Execution)

Run the salary scraper locally to gather the latest salary data:

```bash
python src/salary_scraper.py
```

### Lineup Optimizer (Docker Execution)

To run the lineup optimizer using Docker:

```bash
make run-lineup-optimizer
```

Customize the parameters as needed in `src/lineup_optimizer`

## Customization

The lineup optimizer accepts several parameters:

- `YEAR`: NFL season year (default: current year)
- `WEEK`: Week number (default: current week) 
- `DEF_SALARY`: Salary for defense (default: 0)
- `USE_AVG_FPTS`: Use average fantasy points (default: false)
- `WEIGHTS`: Custom weighting for projections (JSON format)

## Project Structure

```
dfs-lineup-optimizer/
├── src/
│   ├── salary_scraper.py
│   └── lineup_optimizer.py
├── data/
│   ├── salaries/
│   └── lineups/
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Please check the terms of service for DraftKings and any data sources before use.
