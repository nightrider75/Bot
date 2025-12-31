"""Dependencies module for the bot orchestration system.

This module provides database connection management and session handling,
including connection pooling, retry logic, and dependency injection
setup for FastAPI endpoints.
"""

import asyncio
from typing import Annotated

from fastapi import Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import settings

# Create async engine with connection pool configuration
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to False in production
    # Connection pool settings to handle connection expiration
    # Number of connections to maintain in pool
    pool_size=settings.store_config.database_pool_size,
    # Additional connections that can be created on demand
    max_overflow=settings.store_config.database_max_overflow,
    # Timeout to get connection from pool
    pool_timeout=settings.store_config.database_pool_timeout,
    # Recycle connections every 5 mins
    pool_recycle=settings.store_config.database_pool_recycle,
    # Validate connections before use (prevents stale connections)
    pool_pre_ping=settings.store_config.database_pool_pre_ping,
    # Engine options for better error handling
    connect_args={
        "server_settings": {
            "application_name": "bot",
        }
    },
)


class RetryAsyncSession(AsyncSession):
    """Custom AsyncSession with automatic retry middleware for connection issues."""

    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry database operations with exponential backoff for connection issues."""
        if not settings.store_config.database_retry_enabled:
            return await operation(*args, **kwargs)

        last_exception = None
        max_retries = settings.store_config.database_retry_max_attempts
        delay = settings.store_config.database_retry_delay

        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Log specific error types for better debugging
                if (
                    "connection is closed" in error_msg
                    or "underlying connection is closed" in error_msg
                ):
                    logger.warning(
                        f"Database connection closed (attempt {attempt + 1}/{max_retries}): {e}."
                    )
                elif "prepared statement" in error_msg:
                    logger.warning(
                        f"Prepared statement error, connection likely stale (attempt {attempt + 1}/{max_retries}): {e}."
                    )
                else:
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}."
                    )

                if attempt < max_retries - 1:
                    wait_time = delay * (2**attempt)  # Exponential backoff
                    logger.info(
                        f"Retrying database operation in {wait_time:.1f} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Database operation failed after {max_retries} attempts: {e}"
                    )
                    raise

        # This shouldn't be reached, but just in case
        if last_exception:
            raise last_exception

    async def commit(self) -> None:
        """Commit with retry logic."""
        return await self._retry_operation(super().commit)

    async def flush(self, objects=None) -> None:
        """Flush with retry logic."""
        return await self._retry_operation(super().flush, objects)

    async def execute(
        self,
        statement,
        parameters=None,
        execution_options=None,
        bind_arguments=None,
        _parent_execute_state=None,
        _add_event=None,
    ):
        """Execute with retry logic."""
        return await self._retry_operation(
            super().execute,
            statement,
            parameters,
            execution_options,
            bind_arguments,
            _parent_execute_state,
            _add_event,
        )


# Create async session factory with retry middleware
AsyncSessionLocal = async_sessionmaker(
    engine,
    # class_=RetryAsyncSession,  # causes execute() signature issues
    class_=AsyncSession,  # Use regular AsyncSession to avoid execute() parameter mismatch
    expire_on_commit=False,
    # Additional session configuration for better connection handling
    autoflush=True,  # Automatically flush pending changes
    autocommit=False,  # Don't auto-commit (explicit commits only)
)


async def get_session():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
