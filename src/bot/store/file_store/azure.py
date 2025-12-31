import os
from io import BytesIO

from azure.storage.blob.aio import ContainerClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError, AzureError

from bot.store.file_store.types import (
    FileStoreConfig,
    FileStoreTypes,
)


class AzureStore:
    def __init__(self, config: FileStoreConfig):
        self.config = config
        if self.config.file_store_type == FileStoreTypes.AZURE:
            self.container_name = self.config.store_location
            self.azure_prefix = self.config.store_path_prefix or ""
            self.account_url = self.config.account_url

            # Get connection string from environment variable
            if not self.account_url:
                raise ValueError(
                    "STORE_CONFIG__FILE_STORAGE_CONFIG__ACCOUNT_URL environment variable is required for Azure storage"
                )

            # Initialize Azure Blob Service Client
            self.client = ContainerClient(
                account_url=self.account_url,
                container_name=self.container_name,
                credential=DefaultAzureCredential(),
            )
        else:
            raise NotImplementedError(
                f"Invalid store config: {self.config.file_store_type} expected AZURE."
            )

    def _get_full_path(self, destination_path: str) -> str:
        """Get the full blob path with prefix"""
        return os.path.join(self.azure_prefix, destination_path).replace("\\", "/")

    async def save_from_file(
        self, destination_path: str, local_path: str, content_type: str | None = None
    ) -> str:
        """Save a file from local path to Azure Blob Storage"""
        try:
            full_path = self._get_full_path(destination_path)

            # Read file and upload
            with open(local_path, "rb") as data:
                content_settings = None
                if content_type:
                    from azure.storage.blob import ContentSettings

                    content_settings = ContentSettings(content_type=content_type)
                await self.client.upload_blob(
                    name=full_path,
                    data=data,
                    overwrite=True,
                    content_settings=content_settings,
                )

            # https://tpportugal.blob.core.windows.net/test-orchestration-data/a.txt
            return f"{self.account_url}/{self.container_name}/{full_path}"

        except AzureError as e:
            raise Exception(f"Failed to upload file to Azure Blob Storage: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error uploading file: {e}")

    async def save_bytes(
        self, destination_path: str, data: bytes, content_type: str | None = None
    ) -> str | None:
        """Save bytes data directly to Azure Blob Storage"""
        try:
            full_path = self._get_full_path(destination_path)

            # Upload bytes
            content_settings = None
            if content_type:
                from azure.storage.blob import ContentSettings

                content_settings = ContentSettings(content_type=content_type)

            await self.client.upload_blob(
                full_path,
                BytesIO(data),
                overwrite=True,
                content_settings=content_settings,
            )

            return f"{self.account_url}/{self.container_name}/{full_path}"

        except AzureError as e:
            raise Exception(f"Failed to upload bytes to Azure Blob Storage: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error uploading bytes: {e}")

    async def save_from_string(self, destination_path: str, transcript: str) -> str:
        """Save a transcript string to a file in Azure Blob Storage"""
        try:
            transcript_bytes = transcript.encode("utf-8")
            return await self.save_bytes(
                destination_path,
                transcript_bytes,
                content_type="text/plain; charset=utf-8",
            )
        except Exception as e:
            raise Exception(f"Failed to save transcript: {e}")

    async def get_file(self, file_path: str) -> bytes:
        """Retrieve a file from Azure Blob Storage and return its bytes"""
        try:
            full_path = self._get_full_path(file_path)

            # Download blob
            stream = await self.client.download_blob(blob=full_path)

            data = await stream.readall()

            return data

        except ResourceNotFoundError:
            raise FileNotFoundError(
                f'File not found: f"{self.account_url}/{self.container_name}/{full_path}"'
            )
        except AzureError as e:
            raise Exception(f"Failed to retrieve file from Azure Blob Storage: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving file: {e}")

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in Azure Blob Storage"""
        try:
            full_path = self._get_full_path(file_path)

            # Get blob client
            blob_client = self.client.get_blob_client(blob=full_path)

            # Check if blob exists
            return await blob_client.exists()

        except AzureError as e:
            raise Exception(f"Error checking file existence: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error checking file existence: {e}")

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from Azure Blob Storage"""
        try:
            full_path = self._get_full_path(file_path)

            # Delete Blob
            await self.client.delete_blob(blob=full_path)

            return True

        except ResourceNotFoundError:
            # File doesn't exist, consider it successfully deleted
            return False
        except AzureError as e:
            raise Exception(f"Failed to delete file from Azure Blob Storage: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error deleting file: {e}")
