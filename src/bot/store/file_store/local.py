from pathlib import Path

import aiofiles
import mimetypes

from bot.store.file_store.types import (
    FileStoreConfig,
    FileStoreTypes,
)


class LocalStore:
    def __init__(self, config: FileStoreConfig):
        self.config = config
        if self.config.file_store_type == FileStoreTypes.LOCAL:
            if self.config.store_path_prefix:
                self.base_path = (
                    Path(self.config.store_location) / self.config.store_path_prefix
                )
            else:
                self.base_path = Path(self.config.store_location)

            self.base_path.mkdir(parents=True, exist_ok=True)
        else:
            raise NotImplementedError(
                f"Invalid store config: {self.config.file_store_type} expected LOCAL."
            )

    async def save_from_file(
        self, destination_path: str, local_path: str, content_type: str | None = None
    ) -> str:
        # Save a file from local path to the store
        full_path = self.base_path / destination_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(local_path, "rb") as src_file:
            data = await src_file.read()
        async with aiofiles.open(full_path, "wb") as dest_file:
            await dest_file.write(data)
        return str(full_path)

    async def save_from_string(self, destination_path: str, transcript: str) -> str:
        # Save a transcript string to a file in the store
        full_path = self.base_path / destination_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, "w") as dest_file:
            await dest_file.write(transcript)
        return str(full_path)

    async def get_file(self, file_path: str) -> bytes:
        # Retrieve a file from the store and return its bytes
        full_path = self.base_path / file_path
        async with aiofiles.open(full_path, "rb") as f:
            data = await f.read()
        return data

    def _augment_extension(self, path: str, content_type: str) -> str:
        extension = mimetypes.guess_extension(content_type)
        if not extension:
            return f"{path}.raw"
        if not path.endswith(extension):
            return f"{path}.{extension}"
        else:
            return path

    async def save_bytes(
        self, destination_path: str, data: bytes, content_type: str | None = None
    ) -> str | None:
        """Save bytes data directly to Local file"""
        try:  # Save a transcript string to a file in the store
            if content_type:
                destination_path = self._augment_extension(
                    destination_path, content_type=content_type
                )
            full_path = self.base_path / destination_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, "wb") as dest_file:
                await dest_file.write(data)
            return str(full_path)
        except Exception as e:
            raise Exception(f"Unexpected error uploading bytes: {e}")

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from the local store.

        Args:
            file_path: Relative path from base_path, or absolute path that's under base_path

        Returns:
            True if file was deleted, False if file doesn't exist
        """
        try:
            # Handle both relative and absolute paths
            if Path(file_path).is_absolute():
                # If absolute path, check if it's under base_path
                full_path = Path(file_path)
                try:
                    # Verify it's under base_path for security
                    full_path.relative_to(self.base_path)
                except ValueError:
                    # Not under base_path, use as-is (might be a legacy absolute path)
                    full_path = Path(file_path)
            else:
                # Relative path
                full_path = self.base_path / file_path

            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False
