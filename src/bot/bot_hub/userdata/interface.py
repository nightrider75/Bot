from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from bot.bot_hub.types import BotUserData


class UserDataInterface(ABC):
    """
    Interface for user data management operations.

    This interface defines all methods related to managing user data
    including retrieval, modification, and clearing of user data.
    """

    @abstractmethod
    async def get_user_data(self, user_id: str) -> Optional[BotUserData]:
        """
        Get user data for the given bot_identifier and user_id.

        Returns:
            Optional[dict]: User data if available, None otherwise
        """

    @abstractmethod
    async def get_default_user_data(self) -> dict:
        """
        Get default user data.

        Returns:
            dict: Default user data
        """

    @abstractmethod
    async def add_user_data(self, user_data: List[BotUserData]):
        """
        Add user data to the system.

        Args:
            user_data: List of dictionaries containing user data
        """

    @abstractmethod
    async def replace_user_data(self, user_data: List[BotUserData]):
        """
        Replace existing user data with new data.

        Args:
            user_data: Dictionary containing new user data to replace existing data
        """

    @abstractmethod
    async def clear_user_data(self):
        """
        Clear all user data for the current user/session.
        """

    @abstractmethod
    async def list_user_data(self) -> List[BotUserData]:
        """
        List all user data entries.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing user data,
                                 each with 'user_id' and other user data fields
        """

    @abstractmethod
    async def delete_user_data(self, user_id: str) -> bool:
        """
        Delete data for a specific user.

        Args:
            user_id: The user identifier

        Returns:
            bool: True if user data was deleted successfully, False if user not found
        """

    @classmethod
    @abstractmethod
    async def create_bot(cls, bot_id: UUID) -> None:
        """
        Create a new bot userdata setup.

        Args:
            bot_id: The identifier for the new bot

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot creation fails
        """

    @classmethod
    @abstractmethod
    async def delete_bot_userdata(cls, bot_id: UUID) -> None:
        """
        Delete all userdata for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot deletion fails
            FileNotFoundError: If bot userdata doesn't exist
        """
