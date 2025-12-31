"""
Bot Hub User Data routes.

This module provides API endpoints for managing user data in the bot hub.
"""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bot.bot_hub.hub import BotHub
from bot.bot_hub.types import BotUserData

router = APIRouter()


class UserDataRequest(BaseModel):
    """Request model for user data operations."""

    data: Dict[str, str]


class UserDataResponse(BaseModel):
    """Response model for user data operations."""

    key: str
    value: Any


@router.get("/{bot_id}/users/{user_id}/data", response_model=UserDataResponse)
async def get_user_data(bot_id: UUID, user_id: str):
    """
    Get user data for a specific key.

    Args:
        bot_id: The identifier for the bot
        user_id: The identifier for the user

    Returns:
        UserDataResponse: The user data for the specified key
    """
    try:
        hub = BotHub(bot_id)

        value = await hub.userdata_provider.get_user_data(user_id=user_id)
        return UserDataResponse(key=user_id, value=value)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user data: {str(e)}"
        ) from e


@router.post("/{bot_id}/users/{user_id}/data", response_model=UserDataResponse)
async def save_user_data(bot_id: UUID, user_id: str, request: UserDataRequest):
    """
    Save user data for a specific key.

    Args:
        bot_id: The identifier for the bot
        user_id: The identifier for the user
        request: The data key and value to save

    Returns:
        UserDataResponse: Confirmation of the saved data
    """
    try:
        hub = BotHub(bot_id)

        await hub.userdata_provider.add_user_data(
            [BotUserData(user_id=user_id, data=request.data)]
        )
        return UserDataResponse(key=user_id, value=request.data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save user data: {str(e)}"
        ) from e


@router.delete("/{bot_id}/users/{user_id}/data")
async def delete_user_data(bot_id: UUID, user_id: str):
    """
    Delete user data for a specific key.

    Args:
        bot_id: The identifier for the bot
        user_id: The identifier for the user

    Returns:
        dict: Confirmation of deletion
    """
    try:
        hub = BotHub(bot_id)

        success = await hub.userdata_provider.delete_user_data(user_id)
        if success:
            return {"message": f"User data for user '{user_id}' deleted successfully"}
        else:
            raise HTTPException(
                status_code=404, detail=f"User data for user '{user_id}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete user data: {str(e)}"
        ) from e


@router.get("/{bot_id}/users/")
async def list_user_data(bot_id: UUID):
    """
    List all user data keys for a user.

    Args:
        bot_id: The identifier for the bot
        user_id: The identifier for the user

    Returns:
        dict: All user data for the user
    """
    try:
        hub = BotHub(bot_id)

        # Note: This assumes the userdata provider has a method to list all data
        # You may need to implement this method in the userdata interface
        data = await hub.userdata_provider.list_user_data()
        return {"user_data": data}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list user data: {str(e)}"
        ) from e
