from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class FileStoreTypes(StrEnum):
    """Source/storage location for platform assets/transcripts/recordings."""

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


class FileStoreConfig(BaseModel):
    file_store_type: FileStoreTypes = FileStoreTypes.LOCAL
    account_url: Optional[str] = None
    credentials_path: Optional[str] = None
    store_location: str = "data"
    store_path_prefix: Optional[str] = None
