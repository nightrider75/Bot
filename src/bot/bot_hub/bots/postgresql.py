"""
PostgreSQL-based bot provider implementation.

This module provides a bot provider that stores bot data in PostgreSQL database.
"""

from typing import List
from uuid import UUID
from loguru import logger

from sqlalchemy import delete, select

from bot.bot_hub.bots.interface import Bot, BotProviderInterface
from bot.models.bot_models import Bot as BotModel
from bot.deps import AsyncSessionLocal


class PostgreSQLBotProvider(BotProviderInterface):
    """
    PostgreSQL-based bot provider that stores bot data in PostgreSQL database.

    """

    async def create_bot(self, name: str) -> Bot:
        """
        Create a new bot with the given name.

        Args:
            name: The name of the bot to create

        Returns:
            The created bot instance

        Raises:
            RuntimeError: If bot creation fails
        """

        async with AsyncSessionLocal() as session:
            try:
                # Create bot entry
                bot = BotModel(
                    bot_name=name,
                )

                session.add(bot)
                await session.commit()
                await session.refresh(bot)

                logger.info(f"Created bot: {bot.id}")

                return Bot(id=bot.id, name=bot.bot_name)

            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to create bot {name}: {e}")
                raise RuntimeError(f"Bot creation failed: {e}")

    async def get_bot(self, bot_id: UUID) -> Bot:
        """
        Get a bot by its ID.

        Args:
            bot_id: The ID of the bot to retrieve

        Returns:
            The bot instance if found

        Raises:
            FileNotFoundError: If bot with given ID doesn't exist
            RuntimeError: If retrieval fails
        """

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(BotModel).where(BotModel.id == bot_id)
                )
                bot = result.scalar_one_or_none()

                if not bot:
                    raise FileNotFoundError(f"Bot not found: {bot_id}")

                return Bot(
                    id=bot.id, name=bot.bot_name, initial_node_id=bot.start_node_id
                )

            except Exception as e:
                logger.error(f"Failed to get bot {bot_id}: {e}")
                raise RuntimeError(f"Bot retrieval failed: {e}")

    async def update_bot(self, bot_id: UUID, start_node_id: UUID) -> Bot:
        """
        Update a bot via its ID.

        Args:
            bot_id: The ID of the bot to retrieve
            start_node_id: The ID of the starting node to set

        Returns:
            The bot instance
        """

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(BotModel).where(BotModel.id == bot_id)
                )
                bot = result.scalar_one_or_none()

                if not bot:
                    raise FileNotFoundError(f"Bot not found: {bot_id}")
                bot.start_node_id = start_node_id
                await session.commit()
                await session.refresh(bot)
                return Bot(
                    id=bot.id, name=bot.bot_name, initial_node_id=bot.start_node_id
                )

            except Exception as e:
                logger.error(f"Failed to get bot {bot_id}: {e}")
                raise RuntimeError(f"Bot retrieval failed: {e}")

    async def list_bots(self) -> List[Bot]:
        """
        List all available bots.

        Returns:
            List of all bot instances

        Raises:
            RuntimeError: If listing fails
        """

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(BotModel))
                bots = result.scalars().all()
                return [
                    Bot(id=i.id, name=i.bot_name, initial_node_id=i.start_node_id)
                    for i in bots
                ]

            except Exception as e:
                logger.error(f"Failed to list bots: {e}")
                raise RuntimeError(f"Bot listing failed: {e}")

        return bots

    async def delete_bot(self, bot_id: UUID) -> None:
        """
        Delete a bot by its ID.

        Args:
            bot_id: The ID of the bot to delete

        Raises:
            FileNotFoundError: If bot with given ID doesn't exist
            RuntimeError: If deletion fails
        """

        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    delete(BotModel).where(BotModel.id == bot_id)
                )
                await session.commit()

                if result.rowcount == 0:
                    raise FileNotFoundError(f"Bot not found: {bot_id}")

                logger.info(f"Deleted bot: {bot_id}")

            except FileNotFoundError:
                raise
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to delete bot {bot_id}: {e}")
                raise RuntimeError(f"Bot deletion failed: {e}")
