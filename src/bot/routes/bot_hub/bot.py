"""
Bot Hub Bot Management routes.

This module provides API endpoints for managing bot lifecycle operations
including creating, listing, and deleting bots in the bot hub.
"""

from typing import List
from uuid import UUID
from loguru import logger

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from bot.bot_hub.bots import Bot
from bot.bot_hub.hub import BotHub

router = APIRouter()


class BotCreateRequest(BaseModel):
    """Request model for creating a new bot."""

    bot_name: str


class BotResponse(BaseModel):
    """Response model for bot information."""

    bot_id: UUID
    bot_name: str
    message: str


class BotsListResponse(BaseModel):
    """Response model for listing bots."""

    bots: List[Bot]


@router.post("/", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(request: BotCreateRequest):
    """
    Create a new bot with all required provider setups.

    Args:
        request: BotCreateRequest containing the bot_id

    Returns:
        BotResponse: Confirmation of bot creation

    Raises:
        HTTPException: If bot creation fails
    """
    try:
        bot = await BotHub.create_bot(request.bot_name)
        return BotResponse(
            bot_id=str(bot.id),  # Convert UUID to string
            bot_name=bot.name,
            message=f"Bot '{bot.name}' created successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid bot ID: {str(e)}"
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bot: {str(e)}",
        ) from e


@router.get("/{bot_id}", response_model=Bot)
async def get_bot(bot_id: UUID):
    """
    List all available bots across all providers.

    Returns:
        BotsListResponse: List of all bot IDs

    Raises:
        HTTPException: If listing bots fails
    """
    try:
        bots = await BotHub.list_bots()
        logger.debug(f"Retrieved bots: {bots}")
        for bot in bots:
            if bot.id == bot_id:  # Convert UUID to string for comparison
                return bot
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Bot '{bot_id}' not found"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bots: {str(e)}",
        ) from e


@router.get("/", response_model=BotsListResponse)
async def list_bots():
    """
    List all available bots across all providers.

    Returns:
        BotsListResponse: List of all bot IDs

    Raises:
        HTTPException: If listing bots fails
    """
    try:
        bots = await BotHub.list_bots()
        return BotsListResponse(bots=bots)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list bots: {str(e)}",
        ) from e


@router.delete("/{bot_id}", response_model=BotResponse)
async def delete_bot(bot_id: UUID):
    """
    Delete a bot and all its associated data across all providers.

    Args:
        bot_id: The unique identifier of the bot to delete

    Returns:
        BotResponse: Confirmation of bot deletion

    Raises:
        HTTPException: If bot deletion fails
    """
    try:
        await BotHub.delete_bot(bot_id)
        return BotResponse(
            bot_id=bot_id,
            bot_name="",  # Name not available after deletion
            message=f"Bot '{bot_id}' deleted successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid bot ID: {str(e)}"
        ) from e
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Bot not found: {str(e)}"
        ) from e
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bot: {str(e)}",
        ) from e
