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

# Update lock file if pyproject.toml changed (regenerate lock file to sync metadata)
RUN poetry lock || true

# Install dependencies AND the bot package itself (removed --no-root flag)
# This ensures the 'bot' module is installed and the 'app' script entry point works
RUN poetry install --only main && rm -rf $POETRY_CACHE_DIR

# Download NLTK data (punkt_tab) - this is required by the app
RUN poetry run python -c "import nltk; nltk.download('punkt_tab')"

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Create a startup script that ensures .env is created before Python runs
RUN echo '#!/bin/sh\n\
set -e\n\
echo "[STARTUP] ========================================"\n\
echo "[STARTUP] Starting bot orchestration service..."\n\
echo "[STARTUP] ========================================"\n\
echo "[STARTUP] PORT=${PORT:-NOT_SET}"\n\
echo "[STARTUP] WORKERS=${WORKERS:-NOT_SET}"\n\
\n\
# Ensure PORT is set (Cloud Run should set this, but default to 8080)\n\
export PORT=${PORT:-8080}\n\
export WORKERS=${WORKERS:-1}\n\
\n\
echo "[STARTUP] Using PORT=$PORT"\n\
echo "[STARTUP] Using WORKERS=$WORKERS"\n\
\n\
if [ -n "$ENV_FILE" ]; then\n\
  echo "[STARTUP] Creating .env file from ENV_FILE environment variable"\n\
  printf "%s" "$ENV_FILE" > /app/.env\n\
  echo "[STARTUP] .env file created successfully"\n\
  echo "[STARTUP] .env file size: $(wc -c < /app/.env) bytes"\n\
else\n\
  echo "[STARTUP] No ENV_FILE provided, using existing .env or environment variables"\n\
fi\n\
\n\
echo "[STARTUP] ========================================"\n\
echo "[STARTUP] Launching application..."\n\
echo "[STARTUP] ========================================"\n\
exec poetry run app\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]

