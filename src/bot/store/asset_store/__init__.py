"""Asset store module."""

from bot.store.asset_store.interface import (
    AssetStoreInterface,
)
from bot.store.asset_store.postgres import (
    PostgresAssetStore,
)
from bot.store.asset_store.types import (
    FileInfo,
)

__all__ = [
    "AssetStoreInterface",
    "FileInfo",
    "PostgresAssetStore",
]
