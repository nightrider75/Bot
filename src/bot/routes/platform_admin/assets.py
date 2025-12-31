"""Platform routes for asset management."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from bot.routes.platform.dependencies import get_asset_store
from bot.store.asset_store import FileInfo, PostgresAssetStore
from bot.types import AssetType

router = APIRouter()


@router.get("/", response_model=list[FileInfo], response_class=JSONResponse)
async def list_assets(
    asset_store: PostgresAssetStore = Depends(get_asset_store),
):
    """List all platform assets.

    Returns:
        List of FileInfo objects representing all stored files.
    """
    try:
        files = await asset_store.list_files()
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/{file_id}")
async def get_asset(
    file_id: UUID,
    asset_store: PostgresAssetStore = Depends(get_asset_store),
):
    """Get an asset by ID.

    Args:
        file_id: The UUID of the file to retrieve.

    Returns:
        The file content with appropriate content-type header.
    """
    try:
        file_data = await asset_store.get_file(file_id)
        if file_data is None:
            raise HTTPException(status_code=404, detail="File not found")

        # Get file info to determine content type
        files = await asset_store.list_files()
        file_info = next((f for f in files if f.id == file_id), None)

        if file_info is None:
            raise HTTPException(status_code=404, detail="File not found")

        return Response(
            content=file_data,
            media_type=file_info.content_type,
            headers={"Content-Disposition": f'inline; filename="{file_info.name}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file: {str(e)}")


@router.post("/", response_model=FileInfo)
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    asset_store: PostgresAssetStore = Depends(get_asset_store),
):
    """Upload a new asset.

    Args:
        file: The file to upload.
        asset_type: The type of asset. Must be one of the allowed AssetType values (e.g., "initial_audio").

    Returns:
        FileInfo object with details of the uploaded file.
    """
    # Validate asset_type against enum
    try:
        asset_type_enum = AssetType(asset_type)
    except ValueError:
        valid_types = [e.value for e in AssetType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid asset_type '{asset_type}'. Must be one of: {', '.join(valid_types)}",
        )

    try:
        file_data = await file.read()
        content_type = file.content_type or "application/octet-stream"

        file_id = await asset_store.store_file(
            name=file.filename or "untitled",
            blob=file_data,
            content_type=content_type,
            asset_type=asset_type_enum.value,
        )

        # Get the file info
        files = await asset_store.list_files()
        file_info = next((f for f in files if f.id == file_id), None)

        if file_info is None:
            raise HTTPException(
                status_code=500, detail="File stored but could not retrieve info"
            )

        return file_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.delete("/{file_id}")
async def delete_asset(
    file_id: UUID,
    asset_store: PostgresAssetStore = Depends(get_asset_store),
):
    """Delete an asset by ID.

    Args:
        file_id: The UUID of the file to delete.

    Returns:
        Success message.
    """
    try:
        result = await asset_store.delete_file(file_id)

        if not result:
            raise HTTPException(status_code=404, detail="File not found")

        return {"message": "File deleted successfully", "file_id": str(file_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
