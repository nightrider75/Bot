"""
File-based bot provider implementation.

This module provides a bot provider that stores bot data in JSON files.
"""

import json
import os
from uuid import UUID, uuid4
from pathlib import Path
from typing import List

from bot.bot_hub.bots.interface import Bot, BotProviderInterface
from bot.config import settings


class FileBotProvider(BotProviderInterface):
    """
    File-based bot provider that stores bot data in JSON files.

    Each bot is stored in a separate JSON file in a configured directory.
    """

    def __init__(self):
        """
        Initialize the file bot provider.

        Uses the base path from settings to create a 'bots' directory
        for storing bot data files.
        """
        self.base_path = Path(settings.hub_config.data_base_path) / "bots"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_bot_file_path(self, bot_id: UUID) -> Path:
        """Get the file path for a bot's data file."""
        return self.base_path / f"{bot_id}.json"

    def _save_bot(self, bot: Bot) -> None:
        """Save a bot's data to its JSON file."""
        file_path = self._get_bot_file_path(bot.id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(bot.model_dump(mode="json"), f, indent=2)

    def _load_bot(self, bot_id: UUID) -> Bot:
        """Load a bot's data from its JSON file."""
        file_path = self._get_bot_file_path(bot_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Bot {bot_id} not found")

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            return Bot(**data)

    async def create_bot(self, name: str) -> Bot:
        """
        Create a new bot with the given name.

        Args:
            name: The name of the bot to create

        Returns:
            The created bot instance
        """
        bot_id = uuid4()
        bot = Bot(id=bot_id, name=name)
        self._save_bot(bot)
        return bot

    async def get_bot(self, bot_id: UUID) -> Bot:
        """
        Get a bot by its ID.

        Args:
            bot_id: The ID of the bot to retrieve

        Returns:
            The bot instance if found

        Raises:
            FileNotFoundError: If bot with given ID doesn't exist
        """
        return self._load_bot(bot_id)

    async def update_bot(self, bot_id: UUID, start_node_id: UUID) -> Bot:
        """
        Update a bot via its ID.

        Args:
            bot_id: The ID of the bot to retrieve
            start_node_id: The ID of the starting node to set

        Returns:
            The bot instance
        """
        bot = await self.get_bot(bot_id=bot_id)
        bot.initial_node_id = start_node_id
        self._save_bot(bot)
        return bot

    async def list_bots(self) -> List[Bot]:
        """
        List all available bots.

        Returns:
            List of all bot instances
        """
        bots = []
        for file_path in self.base_path.glob("*.json"):
            bot_id = file_path.stem
            try:
                bot = self._load_bot(bot_id)
                bots.append(bot)
            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                # Skip invalid bot files
                continue
        return bots

    async def delete_bot(self, bot_id: UUID) -> None:
        """
        Delete a bot by its ID.

        Args:
            bot_id: The ID of the bot to delete

        Raises:
            FileNotFoundError: If bot with given ID doesn't exist
        """
        file_path = self._get_bot_file_path(bot_id)
        if not file_path.exists():
            raise FileNotFoundError(f"Bot {bot_id} not found")
        os.remove(file_path)
