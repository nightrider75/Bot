"""Types and models for asset store."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from bot.types import AssetType


class FileInfo(BaseModel):
    """Metadata about a stored file."""

    id: UUID
    name: str
    content_type: str
    created_at: datetime
    updated_at: datetime
    asset_type: AssetType


class AssetStoreIndexType(StrEnum):
    """Type of index storage for asset metadata."""

    POSTGRES = "postgres"


class AssetStoreConfig(BaseModel):
    """Configuration for asset store."""

    index_type: AssetStoreIndexType = AssetStoreIndexType.POSTGRES
