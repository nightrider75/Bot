"""Interface for asset store implementations."""

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from bot.store.asset_store.types import FileInfo


class AssetStoreInterface(ABC):
    """Interface for managing platform assets (files)."""

    @abstractmethod
    async def list_files(self) -> List[FileInfo]:
        """List all stored files.

        Returns:
            List of FileInfo objects representing all stored files.
        """
        pass

    @abstractmethod
    async def get_file(self, file_id: UUID) -> bytes | None:
        """Retrieve a file by ID.

        Args:
            file_id: The UUID of the file to retrieve.

        Returns:
            The file content as bytes, or None if the file doesn't exist.
        """
        pass

    @abstractmethod
    async def store_file(
        self, name: str, blob: bytes, content_type: str, asset_type: str
    ) -> UUID:
        """Store a file and return its ID.

        Args:
            name: The name of the file.
            blob: The file content as bytes.
            content_type: The MIME type of the file.
            asset_type: The type of asset (e.g., initial_audio). Required.

        Returns:
            The UUID of the stored file.
        """
        pass

    @abstractmethod
    async def delete_file(self, file_id: UUID) -> bool:
        """Delete a file by ID.

        Args:
            file_id: The UUID of the file to delete.

        Returns:
            True if the file was deleted, False if it doesn't exist.
        """
        pass
