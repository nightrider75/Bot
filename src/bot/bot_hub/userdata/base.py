"""
Local CSV file userdata provider implementation.

This module provides a CSV file-based implementation of the UserDataInterface
that stores user data in CSV files organized by bot identifier.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiofiles
import aiofiles.os
from aiocsv import AsyncDictReader, AsyncDictWriter, AsyncWriter
from loguru import logger

from bot.bot_hub.types import BotUserData
from bot.bot_hub.userdata.interface import UserDataInterface
from bot.config import settings


class LocalCSVUserDataProvider(UserDataInterface):
    """
    Local CSV file-based user data provider.

    This provider stores user data in CSV files using the structure:
    base_path/bot_id.csv

    The CSV file has a 'user_id' column as the primary key, and other columns
    contain JSON-serialized user data fields.
    """

    def __init__(self, bot_id: UUID):
        """
        Initialize the local CSV user data provider for a specific bot.

        Args:
            bot_id: UUID of the bot this provider manages
        """
        self.bot_id: UUID = bot_id
        self.base_path: Path = Path(settings.hub_config.data_base_path) / "userdata"
        self.csv_file_path: Path = self.base_path / f"{self.bot_id}.csv"

        # Ensure the base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Initialized LocalCSVUserDataProvider for bot '{self.bot_id}' and with file: {self.csv_file_path}"
        )

    async def _read_csv_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Read all data from the CSV file.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping user_id to user data
        """
        if not self.csv_file_path.exists():
            return {}

        try:
            async with aiofiles.open(
                self.csv_file_path, "r", encoding="utf-8", newline=""
            ) as csvfile:
                user_data_map = {}

                async for row in AsyncDictReader(csvfile):
                    user_id = row.get("user_id")
                    if user_id:
                        user_data_map[user_id] = row

            return user_data_map
        except Exception as e:
            logger.error(f"Error reading CSV file {self.csv_file_path}: {e}")
            return {}

    async def _write_csv_data(self, user_data_map: Dict[str, Dict[str, Any]]):
        """
        Write all data to the CSV file.

        Args:
            user_data_map: Dictionary mapping user_id to user data
        """
        try:
            # Prepare CSV content
            columns = set(["user_id"])
            for user_id, user_data in user_data_map.items():
                user_data["user_id"] = user_id
                columns.update(user_data.keys())
            columns_list = list(columns)

            async with aiofiles.open(
                self.csv_file_path, "w", encoding="utf-8", newline=""
            ) as csvfile:
                writer = AsyncDictWriter(
                    csvfile, fieldnames=columns_list, restval="", quoting=csv.QUOTE_ALL
                )
                await writer.writeheader()
                for user_data_dict in user_data_map.values():
                    await writer.writerow(user_data_dict)
        except Exception as e:
            logger.error(f"Error writing CSV file {self.csv_file_path}: {e}")
            raise

    async def get_user_data(self, user_id: str) -> Optional[BotUserData]:
        """
        Get user data for a specific user ID.

        Args:
            user_id: The user identifier

        Returns:
            Optional[BotUserData]: User data if available, None otherwise
        """
        user_data_map = await self._read_csv_data()
        user_data = user_data_map.get(user_id, {})

        if user_data is not None:
            logger.debug(
                f"Retrieved user data for user_id '{user_id}' in bot '{self.bot_id}'"
            )
            return BotUserData(user_id=user_id, data=user_data)
        else:
            logger.debug(
                f"No user data found for user_id '{user_id}' in bot '{self.bot_id}'"
            )
            return BotUserData(user_id=user_id, data={})

    async def get_default_user_data(self) -> dict:
        """
        Get default user data.

        Returns:
            dict: First user's data if available, otherwise empty dictionary
        """
        user_data_map = await self._read_csv_data()

        if user_data_map:
            # Get the first user's data (sorted by user_id for consistency)
            first_user_id = sorted(user_data_map.keys())[0]
            first_user_data = user_data_map[first_user_id]
            logger.debug(
                f"Returning default user data from user_id '{first_user_id}' for bot '{self.bot_id}'"
            )
            return first_user_data
        else:
            logger.debug(
                f"No users found, returning empty default user data for bot '{self.bot_id}'"
            )
            return {}

    async def add_user_data(self, user_data: List[BotUserData]):
        """
        Add user data to the system.

        Args:
            user_data: List of BotUserData objects containing user data
        """
        current_data = await self._read_csv_data()

        added_count = 0
        for bot_user_data in user_data:
            user_id = bot_user_data.user_id
            if not user_id:
                logger.warning(
                    f"Skipping user data entry without user_id: {bot_user_data}"
                )
                continue

            # Store the user data
            current_data[user_id] = bot_user_data.data
            added_count += 1

        await self._write_csv_data(current_data)
        logger.info(f"Added {added_count} user data entries for bot '{self.bot_id}'")

    async def replace_user_data(self, user_data: List[BotUserData]):
        """
        Replace existing user data with new data.

        Args:
            user_data: List of BotUserData objects containing new user data
        """
        current_data = await self._read_csv_data()

        replaced_count = 0
        for bot_user_data in user_data:
            user_id = bot_user_data.user_id
            if not user_id:
                logger.error("Cannot replace user data without user_id")
                raise ValueError("BotUserData must contain 'user_id'")

            # Store the user data
            current_data[user_id] = bot_user_data.data
            replaced_count += 1

        await self._write_csv_data(current_data)
        logger.info(
            f"Replaced {replaced_count} user data entries for bot '{self.bot_id}'"
        )

    async def clear_user_data(self):
        """
        Clear all user data for the current bot.
        """
        try:
            # Recreate the CSV file with just headers
            async with aiofiles.open(
                self.csv_file_path, "w", encoding="utf-8", newline=""
            ) as csvfile:
                writer = AsyncWriter(csvfile)
                await writer.writerow(["user_id"])

            logger.info(f"Cleared all user data for bot '{self.bot_id}'")
        except Exception as e:
            logger.error(f"Error clearing user data for bot '{self.bot_id}': {e}")
            raise

    async def list_user_data(self) -> List[BotUserData]:
        """
        List all user data entries.

        Returns:
            List[BotUserData]: List of BotUserData objects containing user data
        """
        user_data_map = await self._read_csv_data()
        user_data_list = []

        for user_id in sorted(user_data_map.keys()):
            user_data = user_data_map[user_id]
            bot_user_data = BotUserData(user_id=user_id, data=user_data)
            user_data_list.append(bot_user_data)

        logger.debug(
            f"Retrieved {len(user_data_list)} user data entries for bot '{self.bot_id}'"
        )
        return user_data_list

    async def delete_user_data(self, user_id: str) -> bool:
        """
        Delete data for a specific user.

        This is a utility method not in the interface but useful for management.

        Args:
            user_id: The user identifier

        Returns:
            bool: True if user data was deleted, False if user not found
        """
        current_data = await self._read_csv_data()

        if user_id not in current_data:
            logger.warning(
                f"Attempted to delete non-existent user data for user_id '{user_id}' in bot '{self.bot_id}'"
            )
            return False

        del current_data[user_id]
        await self._write_csv_data(current_data)
        logger.info(f"Deleted user data for user_id '{user_id}' in bot '{self.bot_id}'")
        return True

    @classmethod
    async def create_bot(cls, bot_id: UUID) -> None:
        """
        Create a new bot userdata setup.

        Args:
            bot_id: The identifier for the new bot

        Raises:
            ValueError: If bot_id is invalid (empty or None)
            RuntimeError: If creating the userdata setup fails
        """
        if not bot_id:
            raise ValueError("Bot ID cannot be empty")

        try:
            # Create the CSV file for the bot
            base_path = Path(settings.hub_config.data_base_path) / "userdata"
            base_path.mkdir(parents=True, exist_ok=True)

            csv_file = base_path / f"{bot_id}.csv"

            # Create empty CSV with header if it doesn't exist
            if not csv_file.exists():
                async with aiofiles.open(
                    csv_file, "w", encoding="utf-8", newline=""
                ) as f:
                    writer = AsyncWriter(f)
                    await writer.writerow(["user_id"])  # Header row
                logger.info(
                    f"Created userdata CSV file for bot '{bot_id}' at {csv_file}"
                )

        except OSError as e:
            logger.error(f"Error creating bot userdata for '{bot_id}': {e}")
            raise RuntimeError(
                f"Failed to create bot userdata for '{bot_id}': {e}"
            ) from e

    @classmethod
    async def delete_bot_userdata(cls, bot_id: UUID) -> None:
        """
        Delete all userdata for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid (empty or None)
            FileNotFoundError: If the bot's userdata file doesn't exist
            RuntimeError: If deletion fails
        """
        if not bot_id or not bot_id.strip():
            raise ValueError("Bot ID cannot be empty")

        try:
            base_path = Path(settings.hub_config.data_base_path) / "userdata"
            csv_file = base_path / f"{bot_id}.csv"

            if not csv_file.exists():
                raise FileNotFoundError(
                    f"Userdata CSV file for bot '{bot_id}' does not exist at {csv_file}"
                )

            await aiofiles.os.remove(csv_file)
            logger.info(f"Deleted userdata CSV file for bot '{bot_id}' at {csv_file}")

        except OSError as e:
            logger.error(f"Error deleting bot userdata for '{bot_id}': {e}")
            raise RuntimeError(
                f"Failed to delete bot userdata for '{bot_id}': {e}"
            ) from e
