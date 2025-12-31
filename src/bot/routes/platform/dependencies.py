"""Shared dependencies for platform routes."""

from bot.config import settings
from bot.deps import SessionDep
from bot.store.asset_store import PostgresAssetStore


async def get_asset_store(
    db_session: SessionDep,
) -> PostgresAssetStore:
    """Get PostgresAssetStore instance with FileStoreConfig dependency.

    Args:
        db_session: Database session dependency

    Returns:
        PostgresAssetStore instance configured with file store settings
    """
    file_store_config = settings.store_config.file_storage_config
    return PostgresAssetStore(file_store_config=file_store_config, session=db_session)
