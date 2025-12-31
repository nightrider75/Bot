"""SQLAlchemy models for platform assets."""

from uuid import uuid4

from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from bot.models.chat import Base
from bot.types import FileStoreTypes, AssetType


class PlatformAsset(Base):
    """Platform asset table for storing files.

    Stores platform-level assets (e.g., initial audio files) with metadata.
    """

    __tablename__ = "platform_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_path = Column(
        String(512), nullable=False
    )  # Path/reference to file in storage (S3/local)
    asset_type = Column(
        SQLEnum(AssetType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )  # Type of asset (e.g., initial_audio)
    asset_source = Column(
        SQLEnum(FileStoreTypes, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )  # Source/storage location (local/s3/gcp)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
