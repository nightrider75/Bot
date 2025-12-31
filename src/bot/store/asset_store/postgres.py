"""PostgreSQL implementation of asset store."""

import os
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.asset import PlatformAsset
from bot.store.asset_store.interface import AssetStoreInterface
from bot.store.asset_store.types import FileInfo
from bot.store.file_store.store import FileStore
from bot.store.file_store.types import FileStoreConfig


class PostgresAssetStore(AssetStoreInterface):
    """PostgreSQL-based asset store.

    Stores file metadata in PostgreSQL and file data in underlying storage (S3/local).
    """

    def __init__(
        self,
        file_store_config: FileStoreConfig,
        session: AsyncSession,
    ):
        """Initialize PostgreSQL asset store.

        Args:
            file_store_config: The FileStoreConfig to use for constructing FileStore.
            session: Database session for queries.
        """
        self.file_store_config = file_store_config
        self.file_store = FileStore(
            config=file_store_config, scoped_prefix="platform_assets"
        )
        self.session = session

    def _normalize_file_path(self, stored_path: str) -> str:
        """Normalize stored file path to relative path for file store operations.

        Args:
            stored_path: The path as stored in the database

        Returns:
            Relative file path suitable for file store operations
        """
        return stored_path

    async def list_files(self) -> list[FileInfo]:
        """List all stored files."""
        result = await self.session.execute(select(PlatformAsset))
        assets = result.scalars().all()

        return [
            FileInfo(
                id=asset.id,
                name=asset.name,
                content_type=asset.content_type,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
                asset_type=asset.asset_type,
            )
            for asset in assets
        ]

    async def get_file(self, file_id: UUID) -> bytes | None:
        """Retrieve a file by ID."""

        result = await self.session.execute(
            select(PlatformAsset).where(PlatformAsset.id == file_id)
        )
        asset = result.scalar_one_or_none()

        if asset is None:
            return None

        try:
            stored_path = asset.file_path
            file_path = self._normalize_file_path(stored_path)
            return await self.file_store.get_file(file_path)
        except Exception:
            return None

    async def store_file(
        self, name: str, blob: bytes, content_type: str, asset_type: str
    ) -> UUID:
        """Store a file and return its ID."""
        from uuid import uuid4

        file_id = uuid4()

        file_extension = os.path.splitext(name)[1] or ""
        destination_path = f"{file_id}{file_extension}"

        file_path = await self.file_store.save_bytes(
            destination_path, blob, content_type=content_type
        )
        asset_source = self.file_store_config.file_store_type.value

        if isinstance(asset_type, str):
            from bot.types import AssetType as AssetTypeEnum

            asset_type_enum = AssetTypeEnum(asset_type)
        else:
            asset_type_enum = asset_type

        asset = PlatformAsset(
            id=file_id,
            name=name,
            content_type=content_type,
            file_path=file_path,
            asset_type=asset_type_enum,
            asset_source=asset_source,
        )
        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)

        return asset.id

    async def delete_file(self, file_id: UUID) -> bool:
        """Delete a file by ID.

        Translation: UUID -> (postgres) -> file path -> (filestore) -> bool
        """
        result = await self.session.execute(
            select(PlatformAsset).where(PlatformAsset.id == file_id)
        )
        asset = result.scalar_one_or_none()

        if asset is None:
            return False

        try:
            stored_path = asset.file_path
            file_path = self._normalize_file_path(stored_path)
            await self.file_store.delete_file(file_path)
        except Exception:
            pass

        await self.session.delete(asset)
        await self.session.commit()

        return True
