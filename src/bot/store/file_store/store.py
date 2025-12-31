from datetime import datetime
from typing import Optional
from uuid import UUID
from loguru import logger

from bot.store.file_store.local import LocalStore
from bot.store.file_store.s3 import S3Store
from bot.store.file_store.azure import AzureStore
from bot.store.file_store.gcs import GCSStore
from bot.store.file_store.types import (
    FileStoreConfig,
    FileStoreTypes,
)


class FileStore:
    def __init__(self, config: FileStoreConfig, scoped_prefix: Optional[str] = None):
        self.config = config
        self.scoped_prefix = scoped_prefix
        if self.config.file_store_type == FileStoreTypes.LOCAL:
            self.client = LocalStore(config)
        elif self.config.file_store_type == FileStoreTypes.S3:
            self.client = S3Store(config)
        elif self.config.file_store_type == FileStoreTypes.AZURE:
            self.client = AzureStore(config)
        elif self.config.file_store_type == FileStoreTypes.GCS:
            self.client = GCSStore(config)
        else:
            raise NotImplementedError(
                f"File store type {self.config.file_store_type} not implemented yet."
            )

    async def save_recording(self, session_id: UUID, local_path: str) -> str | None:
        try:
            destination_path = f"{self.scoped_prefix}/{datetime.now().strftime('%Y/%m/%d')}/{session_id}/recording.mp3"
            return await self.client.save_from_file(
                destination_path, local_path, content_type="audio/mpeg"
            )
        except Exception as e:
            logger.error(
                f"Failed to store recording via {self.config.file_store_type} with error: {e}"
            )
            return None

    async def save_transcript(self, session_id: UUID, transcript: str) -> str | None:
        try:
            destination_path = f"{self.scoped_prefix}/{datetime.now().strftime('%Y/%m/%d')}/{session_id}/transcript.txt"
            return await self.client.save_from_string(destination_path, transcript)
        except Exception as e:
            logger.error(
                f"Failed to store transcript via {self.config.file_store_type} with error: {e}"
            )
            return None

    async def save_bytes(
        self, destination_path: str, data: bytes, content_type: str | None = None
    ) -> str | None:
        """Save bytes data directly to Store"""
        try:
            return await self.client.save_bytes(
                f"{self.scoped_prefix}/{destination_path}",
                data,
                content_type=content_type,
            )
        except Exception as e:
            logger.error(
                f"Failed to save bytes via {self.config.file_store_type} with error: {e}"
            )
            return None

    async def get_file(self, file_path: str) -> bytes | None:
        try:
            return await self.client.get_file(file_path)
        except Exception as e:
            logger.error(
                f"Failed to get file via {self.config.file_store_type} with error: {e}"
            )
            return None

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from the store.

        Args:
            file_path: Path to the file (relative to store base for local, relative for S3)

        Returns:
            True if file was deleted, False otherwise
        """
        try:
            return await self.client.delete_file(file_path)
        except Exception as e:
            logger.error(
                f"Failed to delete file via {self.config.file_store_type} with error: {e}"
            )
            return False
