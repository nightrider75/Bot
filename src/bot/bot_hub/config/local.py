"""
Local file-based configuration provider.

This module provides a file-based implementation of the ConfigInterface
that stores and retrieves configurations from JSON files organized by bot.
"""

import json
from pathlib import Path
from uuid import UUID

import aiofiles
from loguru import logger

from bot.bot_hub.config.interface import ConfigInterface
from bot.config import settings
from bot.types import (
    BotConfig,
)


class LocalFileConfigProvider(ConfigInterface):
    """
    Local file-based configuration provider.

    This provider stores configurations as JSON files in the filesystem using the structure:
    base_path/configs/<bot_id>.json
    """

    def __init__(self):
        """Initialize the local file configuration provider."""
        self.bot_id: UUID = None
        self.base_path: Path = Path(settings.hub_config.data_base_path) / "configs"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.config_path: Path = Path("")
        self._config_cache: BotConfig | None = None

    async def get_config(self, bot_id: UUID) -> BotConfig:
        """
        Load the bot configuration from the JSON file.

        Returns:
            BotConfig: The loaded configuration
        """
        if self._config_cache is not None:
            return self._config_cache

        config_path = self.base_path / f"{bot_id}.json"

        try:
            async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)
                config = BotConfig.model_validate(data)
                self._config_cache = config
                return config
        except Exception as e:
            logger.error(f"Error loading config for bot '{bot_id}': {e}")
            raise

    async def set_config(self, bot_id: UUID, config: BotConfig) -> None:
        """
        Save the bot configuration to the JSON file.

        Args:
            config: The configuration to save
        """
        config_path = self.base_path / f"{bot_id}.json"
        try:
            async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
                await f.write(config.model_dump_json(indent=2))
            self._config_cache = config
        except Exception as e:
            logger.error(f"Error saving config for bot '{bot_id}': {e}")
            raise

    async def delete_bot_config(self, bot_id: UUID) -> None:
        """
        Delete all configuration data for a specific bot.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot deletion fails
            FileNotFoundError: If bot configuration doesn't exist
        """
        config_path = self.base_path / f"{bot_id}.json"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Bot configuration for '{bot_id}' does not exist at {config_path}"
            )

        try:
            config_path.unlink()
            logger.info(f"Deleted bot configuration for '{bot_id}' at {config_path}")
        except Exception as e:
            logger.error(f"Error deleting bot configuration for '{bot_id}': {e}")
            raise RuntimeError(f"Failed to delete bot configuration: {e}") from e
