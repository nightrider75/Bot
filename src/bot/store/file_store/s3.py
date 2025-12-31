import os

import aioboto3
import aiofiles
from botocore.config import Config
from botocore.exceptions import ClientError

from bot.store.file_store.types import (
    FileStoreConfig,
    FileStoreTypes,
)


class S3Store:
    def __init__(self, config: FileStoreConfig):
        self.config = config
        if self.config.file_store_type == FileStoreTypes.S3:
            self.bucket_name = self.config.store_location
            self.s3_prefix = self.config.store_path_prefix or ""
            # Initialize aioboto3 session for reuse
            self.session = aioboto3.Session()

            # Configure retry settings
            self.retry_config = Config(
                retries={
                    "max_attempts": 5,
                    "mode": "adaptive",  # or 'standard', 'legacy'
                },
                max_pool_connections=50,
            )
        else:
            raise NotImplementedError(
                f"Invalid store config: {self.config.file_store_type} expected S3."
            )

    def _get_s3_client(self):
        """Get S3 client context manager"""
        return self.session.client("s3", config=self.retry_config)

    def _get_full_path(self, destination_path: str) -> str:
        """Get the full S3 path with prefix"""
        return os.path.join(self.s3_prefix, destination_path).replace("\\", "/")

    async def save_from_file(
        self, destination_path: str, local_path: str, content_type: str | None = None
    ) -> str:
        """Save a file from local path to S3"""
        try:
            full_path = self._get_full_path(destination_path)

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            async with self._get_s3_client() as s3_client:
                async with aiofiles.open(local_path, "rb") as file:
                    await s3_client.upload_fileobj(
                        file, self.bucket_name, full_path, ExtraArgs=extra_args
                    )

            return f"s3://{self.bucket_name}/{full_path}"

        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error uploading file: {e}")

    async def save_bytes(
        self, destination_path: str, data: bytes, content_type: str | None = None
    ) -> str | None:
        """Save bytes data directly to S3"""
        try:
            full_path = self._get_full_path(destination_path)

            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            from io import BytesIO

            async with self._get_s3_client() as s3_client:
                await s3_client.upload_fileobj(
                    BytesIO(data), self.bucket_name, full_path, ExtraArgs=extra_args
                )

            return f"s3://{self.bucket_name}/{full_path}"

        except ClientError as e:
            raise Exception(f"Failed to upload bytes to S3: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error uploading bytes: {e}")

    async def save_from_string(self, destination_path: str, transcript: str) -> str:
        """Save a transcript string to a file in S3"""
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
        """Retrieve a file from S3 and return its bytes"""
        try:
            full_path = self._get_full_path(file_path)

            async with self._get_s3_client() as s3_client:
                response = await s3_client.get_object(
                    Bucket=self.bucket_name, Key=full_path
                )

                # Read all data from the streaming body
                data = await response["Body"].read()
                return data

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(
                    f"File not found: s3://{self.bucket_name}/{full_path}"
                )
            else:
                raise Exception(f"Failed to retrieve file from S3: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error retrieving file: {e}")

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in S3"""
        try:
            full_path = self._get_full_path(file_path)

            async with self._get_s3_client() as s3_client:
                await s3_client.head_object(Bucket=self.bucket_name, Key=full_path)
                return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise Exception(f"Error checking file existence: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error checking file existence: {e}")

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from S3"""
        try:
            full_path = self._get_full_path(file_path)

            async with self._get_s3_client() as s3_client:
                await s3_client.delete_object(Bucket=self.bucket_name, Key=full_path)
                return True

        except ClientError as e:
            raise Exception(f"Failed to delete file from S3: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error deleting file: {e}")
