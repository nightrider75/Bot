"""
Bot Hub Functions routes.

This module provides API endpoints for managing functions in the bot hub.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bot.bot_hub.functions.interface import BotFunction
from bot.bot_hub.hub import BotHub

router = APIRouter()


class FunctionsListResponse(BaseModel):
    """Response model for listing functions."""

    functions: List[BotFunction]


@router.get("/{bot_id}/available_functions", response_model=FunctionsListResponse)
async def list_functions(bot_id: UUID):
    """
    List all available functions.
    Returns:
        FunctionsListResponse: List of available functions
    """
    try:
        # Maybe use the functions provider directly instead of going through BotHub
        # Will wait for usage to figure this out
        hub = BotHub(bot_id)
        functions = await hub.functions_provider.list_functions()  # Default node

        return FunctionsListResponse(functions=functions)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list functions: {str(e)}"
        ) from e


@router.post(
    "/{bot_id}/test_function/{function_name}", response_model=FunctionsListResponse
)
async def test_function(bot_id: UUID, function_name: str):
    """
    Test a specific function for a bot.

    Args:
        bot_id: The identifier for the bot
        function_name: The name of the function to test

    Returns:
        FunctionsListResponse: List of available functions
    """
    try:
        # Maybe use the functions provider directly instead of going through BotHub
        # Will wait for usage to figure this out
        hub = BotHub(bot_id)
        functions = await hub.functions_provider.list_functions()  # Default node

        return FunctionsListResponse(functions=functions)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to test function: {str(e)}"
        ) from e
