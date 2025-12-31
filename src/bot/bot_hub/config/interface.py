from abc import ABC, abstractmethod
from uuid import UUID

from bot.types import (
    BotConfig,
)


class ConfigInterface(ABC):
    """
    Interface for configuration management operations.

    This interface defines all methods related to managing various
    configuration objects for the bot components.
    """

    @abstractmethod
    async def set_config(self, bot_id: UUID, config: BotConfig) -> None:
        """
        Set the Bot configuration
        """

    @abstractmethod
    async def get_config(self, bot_id: UUID) -> BotConfig:
        """
        Get the Bot configuration

        Returns:
            BotConfig: The bot configuration containgin the complete bot behaviour configuration
        """

    @abstractmethod
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
