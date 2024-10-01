# DraftKings NFL DFS Lineup Optimizer

This repository contains a Python-based lineup optimizer for DraftKings NFL daily fantasy sports (DFS) contests. It scrapes salary data and projections, then uses optimization techniques to generate optimal lineups.

## Features

- Scrapes NFL DFS salary data from DraftDime
- Retrieves PPR projection data from FantasyPros  
- Optimizes lineups for DraftKings NFL contests
- Allows customization of optimization parameters
- Outputs optimal weekly lineups

You're right, I should have included those additional requirements. Let's update the README to include instructions for installing Docker, Make, and WebDriver. Here's a revised version of the Installation section:

## Installation

1. Clone the repository:

```bash
git clone https://github.com/username/dfs_lineup_optimizer.git
cd dfs_lineup_optimizer
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Docker:

Docker is required to run the lineup optimizer. Follow the official Docker installation guide for your operating system:
- [Install Docker on Windows](https://docs.docker.com/desktop/install/windows-install/)
- [Install Docker on Mac](https://docs.docker.com/desktop/install/mac-install/)
- [Install Docker on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

4. Install Make:

Make is used to simplify the Docker commands. Installation instructions vary by operating system:
- Windows: Install [Chocolatey](https://chocolatey.org/install) and then run `choco install make`
- Mac: Make should be pre-installed. If not, install Xcode Command Line Tools with `xcode-select --install`
- Ubuntu: Run `sudo apt-get install make`

5. Install WebDriver:

WebDriver is required for web scraping. Install the appropriate WebDriver for your preferred browser:
- [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads) for Google Chrome
- [GeckoDriver](https://github.com/mozilla/geckodriver/releases) for Firefox

Make sure to add the WebDriver to your system's PATH.

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
