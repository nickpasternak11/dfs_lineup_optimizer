# Use Python 3.10 as base image
FROM python:3.10-slim as base

# Set the working directory inside the container
WORKDIR /app

# Copy your requirements.txt if you have any, or create one
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

FROM base as salary-scraper

CMD ["python", "src/salary_scraper.py"]

FROM base as lineup-optimizer

CMD ["python", "src/lineup_optimizer.py"]
