"""
In-memory implementation of the UserDataInterface.

This module provides a simple in-memory implementation of the UserDataInterface
that stores all data in memory, useful for testing or simple deployments.
"""

from typing import Dict, List, Optional
from uuid import UUID

from bot.bot_hub.types import BotUserData
from bot.bot_hub.userdata.interface import UserDataInterface


class InMemoryUserDataProvider(UserDataInterface):
    """
    In-memory implementation of UserDataInterface.

    This provider stores all user data in memory using dictionaries. Data is lost
    when the process restarts. Useful for testing or simple deployments.
    """

    _bot_data: Dict[str, Dict[str, BotUserData]] = {}  # bot_id -> {user_id -> data}
    _default_data: Dict[str, dict] = {}  # bot_id -> default data

    def __init__(self):
        """Initialize the in-memory provider."""
        self.bot_id: Optional[str] = None

    async def get_user_data(self, user_id: str) -> BotUserData:
        """
        Get user data for the given user_id.

        Args:
            user_id: The user identifier

        Returns:
            Optional[BotUserData]: User data if available, None otherwise
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        return self._bot_data[self.bot_id].get(
            user_id, BotUserData(user_id=user_id, data={})
        )

    async def get_default_user_data(self) -> dict:
        """
        Get default user data.

        Returns:
            dict: Default user data
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        return self._default_data.get(self.bot_id, {})

    async def add_user_data(self, user_data: List[BotUserData]):
        """
        Add user data to the system.

        Args:
            user_data: List of BotUserData containing user data
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        for data in user_data:
            self._bot_data[self.bot_id][data.user_id] = data

    async def replace_user_data(self, user_data: List[BotUserData]):
        """
        Replace existing user data with new data.

        Args:
            user_data: List of BotUserData containing user data
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        # Clear existing data for these users
        for data in user_data:
            if data.user_id in self._bot_data[self.bot_id]:
                del self._bot_data[self.bot_id][data.user_id]

        # Add new data
        await self.add_user_data(user_data)

    async def clear_user_data(self):
        """
        Clear all user data for the current bot.
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        self._bot_data[self.bot_id].clear()

    async def list_user_data(self) -> List[BotUserData]:
        """
        List all user data entries.

        Returns:
            List[BotUserData]: List of user data entries
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        return list(self._bot_data[self.bot_id].values())

    async def delete_user_data(self, user_id: str) -> bool:
        """
        Delete data for a specific user.

        Args:
            user_id: The user identifier

        Returns:
            bool: True if user data was deleted successfully, False if user not found
        """
        if not self.bot_id:
            raise RuntimeError("Provider not initialized with bot_id")

        if user_id in self._bot_data[self.bot_id]:
            del self._bot_data[self.bot_id][user_id]
            return True
        return False

    @classmethod
    async def create_bot(cls, bot_id: UUID) -> None:
        """
        Create a new bot userdata setup.

        Args:
            bot_id: The identifier for the new bot

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot already exists
        """
        if not bot_id:
            raise ValueError("Invalid bot_id")
        if bot_id in cls._bot_data:
            raise RuntimeError(f"Bot {bot_id} already exists")

        cls._bot_data[bot_id] = {}
        cls._default_data[bot_id] = {}

    @classmethod
    async def delete_bot_userdata(cls, bot_id: UUID) -> None:
        """
        Delete all userdata for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid
            FileNotFoundError: If bot userdata doesn't exist
        """
        if not bot_id:
            raise ValueError("Invalid bot_id")
        if bot_id not in cls._bot_data:
            raise FileNotFoundError(f"Bot {bot_id} not found")

        del cls._bot_data[bot_id]
        if bot_id in cls._default_data:
            del cls._default_data[bot_id]
