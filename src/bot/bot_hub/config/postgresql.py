"""
PostgreSQL-based configuration provider.

This module provides a PostgreSQL implementation of the ConfigInterface
that stores and retrieves configurations from PostgreSQL
"""

from uuid import UUID
from loguru import logger
from sqlalchemy import delete, select

from bot.bot_hub.config.interface import ConfigInterface
from bot.deps import AsyncSessionLocal
from bot.models.bot_models import Config
from bot.types import (
    BotConfig,
)


class PostgreSQLConfigProvider(ConfigInterface):
    """
    PostgreSQL-based configuration provider.

    This provider stores configurations in PostgreSQL database
    """

    def __init__(self):
        """Initialize the PostgreSQL configuration provider."""
        self.bot_id: UUID = ""

    async def get_config(self, bot_id: UUID) -> BotConfig:
        """
        Get the complete bot configuration from PostgreSQL.

        Returns:
            BotConfig: The complete configuration for this bot
        """

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(Config).where(Config.bot_id == bot_id)
                )
                config_obj = result.scalar_one_or_none()

                if not config_obj:
                    raise FileNotFoundError(
                        f"Configuration not found for bot: {bot_id}"
                    )

                return BotConfig(**config_obj.config)

            except FileNotFoundError:
                raise
            except Exception as e:
                logger.error(f"Failed to get config for bot {bot_id}: {e}")
                raise RuntimeError(f"Configuration retrieval failed: {e}")

    async def set_config(self, bot_id: UUID, config: BotConfig):
        """
        Set the complete bot configuration to PostgreSQL.
        """
        config.bot_identifier = bot_id

        async with AsyncSessionLocal() as session:
            try:
                # Check if config exists
                result = await session.execute(
                    select(Config).where(Config.bot_id == bot_id)
                )
                config_obj = result.scalar_one_or_none()

                if config_obj:
                    # Update existing config
                    config_obj.config = config.model_dump(mode="json")
                else:
                    # Create new config
                    config_obj = Config(
                        bot_id=config.bot_identifier,
                        config=config.model_dump(mode="json"),
                    )
                    session.add(config_obj)

                await session.commit()
                logger.info(f"Saved {config} configuration")
                return True

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save configurations: {e}")
                raise RuntimeError(f"Configuration save failed: {e}")

    async def delete_bot_config(cls, bot_id: UUID) -> None:
        """
        Delete all configuration data for a specific bot from PostgreSQL.

        Args:
            bot_id: The identifier for the bot to delete

        Raises:
            ValueError: If bot_id is invalid
            RuntimeError: If bot deletion fails
            FileNotFoundError: If bot configuration doesn't exist
        """

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    delete(Config).where(Config.bot_id == bot_id)
                )
                config_obj = result.scalar_one_or_none()

                if not config_obj:
                    raise FileNotFoundError(
                        f"Configuration not found for bot: {bot_id}"
                    )
                await session.commit()

            except FileNotFoundError:
                raise
            except Exception as e:
                logger.error(f"Failed to get config for bot {bot_id}: {e}")
                raise RuntimeError(f"Configuration retrieval failed: {e}")

        logger.info(f"Deleted bot configuration from PostgreSQL: {bot_id}")
