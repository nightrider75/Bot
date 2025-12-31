"""
Bot provider interface.

This module defines the interface that all bot providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from bot.bot_hub.types import Bot


class BotProviderInterface(ABC):
    """
    Interface that all bot providers must implement.

    This interface defines the standard methods for managing bots
    through different storage backends.
    """

    @abstractmethod
    async def create_bot(self, name: str) -> Bot:
        """
        Create a new bot with the given name.

        Args:
            name: The name of the bot to create

        Returns:
            The created bot instance
        """

    @abstractmethod
    async def get_bot(self, bot_id: UUID) -> Bot:
        """
        Get a bot by its ID.

        Args:
            bot_id: The ID of the bot to retrieve

        Returns:
            The bot instance if found
        """

    @abstractmethod
    async def update_bot(self, bot_id: UUID, start_node_id: UUID) -> Bot:
        """
        Update a bot via its ID.

        Args:
            bot_id: The ID of the bot to retrieve
            start_node_id: The ID of the starting node to set

        Returns:
            The bot instance
        """

    @abstractmethod
    async def list_bots(self) -> List[Bot]:
        """
        List all available bots.

        Returns:
            List of all bot instances
        """

    @abstractmethod
    async def delete_bot(self, bot_id: UUID) -> None:
        """
        Delete a bot by its ID.

        Args:
            bot_id: The ID of the bot to delete
        """
