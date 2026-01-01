# Use Python 3.11 as base image
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.3

# Configure Poetry: Don't create virtual environment, install dependencies to system
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set work directory
WORKDIR /app

# Copy everything first (needed for submodules and local dependencies)
COPY . .

# Submodules are already cloned during checkout, so they're copied as directories
# No need to run git submodule update (and .git is excluded anyway)

# Configure Poetry to not require package metadata validation
RUN poetry config virtualenvs.create false

# Install dependencies (use --no-root to skip building the package itself)
# Also use --no-cache to avoid cache issues
RUN poetry install --no-dev --no-root --no-cache && rm -rf $POETRY_CACHE_DIR

# Download NLTK data (punkt_tab) - this is required by the app
RUN poetry run python -c "import nltk; nltk.download('punkt_tab')"

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Create .env from ENV_FILE if provided, then start the application
CMD sh -c 'if [ -n "$ENV_FILE" ]; then printf "%s" "$ENV_FILE" > /app/.env && echo "Created .env file from ENV_FILE environment variable"; fi && poetry run app'

