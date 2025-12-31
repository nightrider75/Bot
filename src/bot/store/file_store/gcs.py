import os
from typing import Optional
from loguru import logger

from google.cloud import storage
from google.oauth2 import service_account
from google.api_core import exceptions as gcp_exceptions

from bot.store.file_store.types import (
    FileStoreConfig,
    FileStoreTypes,
)


class GCSStore:
    def __init__(self, config: FileStoreConfig):
        self.config = config
        if self.config.file_store_type == FileStoreTypes.GCS:
            self.bucket_name = self.config.store_location
            self.path_prefix = self.config.store_path_prefix or ""

            # Initialize GCP Storage client with credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.config.credentials_path
            )
            self.storage_client = storage.Client(credentials=credentials)
            self.bucket = self.storage_client.bucket(self.bucket_name)
        else:
            raise NotImplementedError(
                f"Invalid store config: {self.config.file_store_type} expected GCP."
            )

    def _get_full_path(self, destination_path: str) -> str:
        """Get the full GCS path with prefix"""
        return os.path.join(self.path_prefix, destination_path).replace("\\", "/")

    async def save_from_file(
        self, destination_path: str, local_path: str, content_type: Optional[str] = None
    ) -> str:
        """Save a file from local path to GCS"""
        try:
            full_path = self._get_full_path(destination_path)
            blob = self.bucket.blob(full_path)

            if content_type:
                blob.content_type = content_type

            # Read and upload file asynchronously
            logger.debug(
                f"Uploading file to GCS: {local_path} -> gs://{self.bucket_name}/{full_path}"
            )
            res = blob.upload_from_filename(local_path, content_type=content_type)
            logger.info(f"GCS File Upload result: {res}")

            return f"gs://{self.bucket_name}/{full_path}"

        except gcp_exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to upload file to GCS: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error uploading file: {e}")

    async def save_bytes(
        self, destination_path: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        """Save bytes data directly to GCS"""
        try:
            full_path = self._get_full_path(destination_path)
            blob = self.bucket.blob(full_path)

            if content_type:
                blob.content_type = content_type

            res = blob.upload_from_string(data, content_type=content_type)
            logger.info(f"GCS Bytes Upload result: {res}")

            return f"gs://{self.bucket_name}/{full_path}"

        except gcp_exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to upload bytes to GCS: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error uploading bytes: {e}")

    async def save_from_string(self, destination_path: str, transcript: str) -> str:
        """Save a transcript string to a file in GCS"""
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
        """Retrieve a file from GCS and return its bytes"""
        try:
            full_path = self._get_full_path(file_path)
            blob = self.bucket.blob(full_path)

            if not blob.exists():
                raise FileNotFoundError(
                    f"File not found: gs://{self.bucket_name}/{full_path}"
                )

            data = blob.download_as_bytes()
            return data

        except gcp_exceptions.NotFound:
            raise FileNotFoundError(
                f"File not found: gs://{self.bucket_name}/{full_path}"
            )
        except gcp_exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to retrieve file from GCS: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving file: {e}")

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in GCS"""
        try:
            full_path = self._get_full_path(file_path)
            blob = self.bucket.blob(full_path)
            return blob.exists()

        except gcp_exceptions.GoogleAPIError as e:
            raise Exception(f"Error checking file existence: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error checking file existence: {e}")

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from GCS"""
        try:
            full_path = self._get_full_path(file_path)
            blob = self.bucket.blob(full_path)
            blob.delete()
            return True

        except gcp_exceptions.NotFound:
            # File doesn't exist, consider it a successful deletion
            return True
        except gcp_exceptions.GoogleAPIError as e:
            raise Exception(f"Failed to delete file from GCS: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error deleting file: {e}")
