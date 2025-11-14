FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry: don't create virtual env (we're in Docker)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /app

# Copy Poetry files and source code (needed for installation)
COPY pyproject.toml poetry.lock* ./
COPY src/ src/

# Install dependencies (including dev for lint/typecheck/test)
RUN poetry install && rm -rf $POETRY_CACHE_DIR

# Copy rest of application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app/src

# Default command
CMD ["poetry", "run", "bot", "--help"]
