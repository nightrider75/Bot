"""
BotStoreInterface for unified bot data access.

This module provides the BotStoreInterface class that serves as a unified interface
for accessing and managing all bot-related data including prompts, functions,
configuration, and user data.
"""

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from bot.bot_hub.types import BotNode, BotUserData, BotNodeMeta
from bot.types import BotConfig


class BotStoreInterface(ABC):
    """
    Interface for unified bot data storage and retrieval operations.

    This interface provides a unified way to access and manage all bot-related data
    including prompts, functions, configuration, and user data across different
    storage backends.
    """

    @abstractmethod
    def __init__(self, bot_id: UUID):
        """
        Initialize the bot store interface with a specific bot ID.

        Args:
            bot_id: The identifier for the bot this store will serve
        """
        self.bot_id = bot_id

    @abstractmethod
    async def get_node(self, node_id: UUID) -> BotNode:
        """
        Get the specific node with its complete data.

        Args:
            node_id: The identifier of the node to get

        Returns:
            BotNode: The complete node object with id and prompt content

        Raises:
            ValueError: If node_id is invalid
            FileNotFoundError: If the node doesn't exist
        """

    @abstractmethod
    async def get_config(self) -> BotConfig:
        """
        Get the complete bot configuration.

        Returns:
            BotConfig: The complete bot configuration including all components

        Raises:
            RuntimeError: If configuration retrieval fails
        """

    @abstractmethod
    async def get_user_data(self, user_id: str) -> BotUserData:
        """
        Get user data for a specific user.

        Args:
            user_id: The identifier for the user

        Returns:
            BotUserData: Structured user data object

        Raises:
            ValueError: If user_id is invalid
            FileNotFoundError: If user data doesn't exist
        """

    @abstractmethod
    async def save_prompts(self, prompts: List[BotNode]) -> bool:
        """
        Save multiple node prompts.

        Args:
            prompts: List of BotNode objects containing node data

        Returns:
            bool: True if all prompts were saved successfully

        Raises:
            ValueError: If prompt data is invalid
            RuntimeError: If saving fails
        """

    @abstractmethod
    async def save_config(self, configs: List[BotConfig]) -> bool:
        """
        Save bot configurations.

        Args:
            configs: List of BotConfig objects to save

        Returns:
            bool: True if all configurations were saved successfully

        Raises:
            ValueError: If config data is invalid
            RuntimeError: If saving fails
        """

    @abstractmethod
    async def save_user_data(self, user_data_list: List[BotUserData]) -> bool:
        """
        Save user data for multiple users.

        Args:
            user_data_list: List of BotUserData objects containing structured user data

        Returns:
            bool: True if all user data was saved successfully

        Raises:
            ValueError: If user data is invalid
            RuntimeError: If saving fails
        """

    @abstractmethod
    async def list_nodes(self) -> List[BotNodeMeta]:
        """
        List all available nodes for this bot.

        Returns:
            List[BotNodeMeta]: List of nodes available for this bot

        Raises:
            RuntimeError: If listing nodes fails
        """

    @abstractmethod
    async def get_all_nodes(self) -> List[BotNode]:
        """
        Get all nodes with their complete data for this bot.

        Returns:
            List[BotNode]: List of complete node objects for this bot

        Raises:
            RuntimeError: If retrieving nodes fails
        """

    @abstractmethod
    async def list_users(self) -> List[str]:
        """
        List all users that have data for this bot.

        Returns:
            List[str]: List of user IDs that have data for this bot

        Raises:
            RuntimeError: If listing users fails
        """

    @abstractmethod
    async def get_all_user_data(self) -> List[BotUserData]:
        """
        Get all user data for this bot.

        Returns:
            List[BotUserData]: List of all user data objects for this bot

        Raises:
            RuntimeError: If retrieving user data fails
        """

    @abstractmethod
    async def delete_prompt(self, node_id: UUID) -> bool:
        """
        Delete prompt for a specific node.

        Args:
            node_id: The identifier of the node to delete the prompt for

        Returns:
            bool: True if prompt was deleted successfully

        Raises:
            ValueError: If node_id is invalid
            FileNotFoundError: If prompt doesn't exist
        """

    @abstractmethod
    async def delete_functions(self, node_id: UUID) -> bool:
        """
        Delete all functions for a specific node.

        Args:
            node_id: The identifier of the node to delete functions for

        Returns:
            bool: True if functions were deleted successfully

        Raises:
            ValueError: If node_id is invalid
        """

    @abstractmethod
    async def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all data for a specific user.

        Args:
            user_id: The identifier for the user

        Returns:
            bool: True if user data was deleted successfully

        Raises:
            ValueError: If user_id is invalid
            FileNotFoundError: If user data doesn't exist
        """
