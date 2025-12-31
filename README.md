# Bot Orchestration

A FastAPI-based orchestration service for managing voice bot interactions across multiple telephony providers (Twilio, Plivo).

## Quick Start

### 1. Initialize Submodules
```bash
git submodule update --init --recursive
```

### 2. Install Dependencies
```bash
poetry install
```

### 3. Database Migrations
**IMPORTANT**: Always run migrations before starting the application.

```bash
# Run all pending migrations
poetry run alembic upgrade head
```

### 4. Start the Server
```bash
poetry run app
```

The API will be available at `http://localhost:8000`

## Database Migration Commands

```bash
# Check current migration status
poetry run alembic current

# Run migrations to latest version
poetry run alembic upgrade head

# Create a new migration (after model changes)
poetry run alembic revision --autogenerate -m "description of changes"
poetry run alembic upgrade head
```
