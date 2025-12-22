# Base Image
FROM python:3.11-slim

# System Deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (The Python Package Manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set Workdir
WORKDIR /app

# Copy Project
COPY . .

# Install Python Deps
# Creating a virtual environment is handled by uv automatically or we can force system install.
# Since we are in a container, we can install directly to system or let uv manage venv.
# Let's verify pyproject.toml exists? If not, we install manually.
# Assuming user might not have pyproject.toml yet, we install dependencies manually for safety.
RUN uv pip install --system ccxt pandas numpy python-dotenv ta-lib

# Environment Variables
ENV PYTHONUNBUFFERED=1

# Default Command (Paper Mode, 7 Days)
CMD ["python", "main.py", "--mode", "paper", "--days", "7.0"]
