"""
Default settings-based configuration provider.

This module provides a default implementation of the ConfigInterface
that retrieves configuration from the server's environment-based settings.
"""

from uuid import UUID

from bot.bot_hub.config.interface import ConfigInterface
from bot.config import settings
from bot.types import (
    BotConfig,
)


class DefaultSettingsConfigProvider(ConfigInterface):
    """
    Default configuration provider that uses server environment settings.

    This provider retrieves all configuration values from the global settings
    object defined in config.py, which reads from environment variables and
    configuration files.
    """

    async def set_config(self, bot_id: UUID, config: BotConfig) -> None:
        """
        Set the Bot configuration
        """
        pass

    async def get_config(self, bot_id: UUID) -> BotConfig:
        """
        Get the Bot configuration

        Returns:
            BotConfig: The bot configuration containgin the complete bot behaviour configuration
        """
        return BotConfig(
            bot_identifier=bot_id,
            pipeline_config=settings.pipeline_config,
            tts=settings.synthesizer_config,
            stt=settings.transcriber_config,
            llm=settings.agent_config,
            transport=settings.transport_config,
            file_store=settings.store_config.file_storage_config,
        )

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
        pass
