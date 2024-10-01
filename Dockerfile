# Use Python 3.10 as base image
FROM python:3.10-slim as base

# Set the working directory inside the container
WORKDIR /app

# Copy your requirements.txt if you have any, or create one
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

FROM base as dfs-optimizer

# Define the command to run your application
CMD ["python", "src/lineup_optimizer.py"]
