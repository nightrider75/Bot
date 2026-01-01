"""Main application module for the bot orchestration system.

This module initializes and configures the FastAPI application, sets up logging,
CORS middleware, and includes all route handlers. It also manages application
lifecycle events for database connections and other resources.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import nltk
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger


from bot.auth import get_current_username
from bot.config import settings
from bot.routes.lib import router
from bot.routes.platform.lib import router as platform_router

# Log early to show module is loading
print(f"[STARTUP] Bot app module loading... PORT={settings.port}", flush=True)

nltk.download("punkt_tab")

# Configure logging - output JSON to stdout for Vector to consume
logger.remove()

# Console output with structured JSON format for Vector
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    serialize=True,
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


@asynccontextmanager
async def lifespan(_fastapi_app: FastAPI):
    """Manage application lifecycle events.

    This context manager handles startup and shutdown events for the FastAPI application,
    including database connection pooling and resource cleanup.

    Args:
        _fastapi_app: The FastAPI application instance
    """
    # global db_pool
    # db_pool = await init_db_pool()
    # set_db_pool(db_pool)
    yield
    # db_pool = await close_db_pool(db_pool)


app = FastAPI(
    title="Bot deployment",
    version="0.1.0",
    openapi_url=settings.openapi_url,
    lifespan=lifespan,
    debug=True,
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(
    platform_router,
    tags=["Platform"],
    dependencies=[Depends(get_current_username)],
)


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for Cloud Run and load balancers."""
    return {
        "status": "healthy",
        "service": "bot-orchestration",
        "port": settings.port,
        "workers": settings.workers
    }


# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/demo", include_in_schema=False)
async def demo_page():
    """Serve the Demo Agents page."""
    return FileResponse(STATIC_DIR / "demo.html")


# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    logger.info(f"Starting bot orchestration Service... with {settings}")
    logger.info(f"Server will listen on 0.0.0.0:{settings.port}")
    logger.info(f"Workers: {settings.workers}")
    try:
        uvicorn.run(
            "bot.app:app",
            host="0.0.0.0",
            port=settings.port,
            workers=settings.workers,
        )
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    main()
