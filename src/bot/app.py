"""Main application module for the bot orchestration system.

This module initializes and configures the FastAPI application, sets up logging,
CORS middleware, and includes all route handlers. It also manages application
lifecycle events for database connections and other resources.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Load environment variables from .env file FIRST (before any other imports)
from dotenv import load_dotenv
load_dotenv()

import nltk
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger


from bot.auth import get_current_username
from bot.config import settings
from bot.routes.lib import router
from bot.routes.platform.lib import router as platform_router
from bot.routes.contact_form import router as contact_form_router

# Log early to show module is loading
import os
print(f"[STARTUP] Bot app module loading...", flush=True)
print(f"[STARTUP] Environment PORT={os.environ.get('PORT', 'NOT SET')}", flush=True)
print(f"[STARTUP] Settings PORT={settings.port}", flush=True)
print(f"[STARTUP] Workers={settings.workers}", flush=True)
print(f"[STARTUP] WEBRTC_ICE_SERVERS={os.environ.get('WEBRTC_ICE_SERVERS', 'NOT SET')}", flush=True)
print(f"[STARTUP] WEBRTC_TURN_USERNAME={os.environ.get('WEBRTC_TURN_USERNAME', 'NOT SET')}", flush=True)
print(f"[STARTUP] WEBRTC_TURN_CREDENTIAL={'***' if os.environ.get('WEBRTC_TURN_CREDENTIAL') else 'NOT SET'}", flush=True)

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
app.include_router(contact_form_router, tags=["Contact Form"])


# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Custom handler for validation errors that returns clear, frontend-friendly messages."""
    
    # Get the first error
    if exc.errors():
        error = exc.errors()[0]
        field = error.get("loc", [])[-1] if error.get("loc") else "unknown"
        msg = error.get("msg", "Validation error")
        input_val = error.get("input", "")
        
        # Format phone number errors
        if field == "phone":
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": "❌ Invalid phone number",
                    "field": "phone",
                    "provided": str(input_val),
                    "message": "Phone number must be exactly 10 digits",
                    "accepted_formats": [
                        "✓ Plain: 1234567890",
                        "✓ With dashes: 123-456-7890",
                        "✓ With parentheses: (123) 456-7890"
                    ]
                }
            )
        
        # Format email errors
        elif field == "email":
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": "❌ Invalid email address",
                    "field": "email",
                    "provided": str(input_val),
                    "message": "Email must be in valid format: example@domain.com",
                    "example": "john@example.com"
                }
            )
        
        # Format required field errors
        elif field in ["firstName", "lastName", "message"]:
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": f"❌ {field} is required",
                    "field": field,
                    "message": f"{field} cannot be empty"
                }
            )
    
    # Default fallback
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "❌ Validation error",
            "message": "Please check your form data and try again"
        }
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
    """Start the uvicorn server.
    
    Reads PORT from environment variable (set by Cloud Run) or falls back to settings.port.
    Always binds to 0.0.0.0 to accept external connections.
    """
    import os
    
    # Cloud Run sets PORT environment variable - we must use it
    # Environment variables take precedence over settings
    port = int(os.environ.get('PORT', settings.port))
    workers = int(os.environ.get('WORKERS', settings.workers))
    
    logger.info("="*60)
    logger.info("Starting Bot Orchestration Service")
    logger.info("="*60)
    logger.info(f"Environment PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"Environment WORKERS: {os.environ.get('WORKERS', 'not set')}")
    logger.info(f"Settings port: {settings.port}")
    logger.info(f"Settings workers: {settings.workers}")
    logger.info(f"Using port: {port}")
    logger.info(f"Using workers: {workers}")
    logger.info(f"Server will listen on 0.0.0.0:{port}")
    logger.info("="*60)
    
    try:
        uvicorn.run(
            "bot.app:app",
            host="0.0.0.0",
            port=port,
            workers=workers,
            log_level=settings.log_level.lower(),
        )
    except Exception as e:
        logger.exception(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    main()
