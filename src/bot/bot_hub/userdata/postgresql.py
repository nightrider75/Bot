"""PostgreSQL-backed user data provider implementation."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from bot.bot_hub.types import BotUserData
from bot.deps import AsyncSessionLocal
from bot.models.bot_models import BotUserData as BotUserDataModel

logger = logging.getLogger(__name__)


class PostgreSQLUserDataProvider:
    """
    PostgreSQL provider for bot user data.

    This provider is initialized per-bot (bot_id stored on init).
    All methods operate on the bot's data without needing bot_id parameter.
    """

    def __init__(self, bot_id: UUID):
        """
        Initialize PostgreSQL provider for a specific bot.

        Args:
            bot_id: UUID of the bot this provider manages
        """
        self.bot_id = bot_id
        logger.info(f"Initialized PostgreSQLUserDataProvider for bot {bot_id}")

    async def get_user_data(self, user_id: str) -> Optional[BotUserData]:
        """
        Get data for a specific user.

        Args:
            user_id: User identifier

        Returns:
            BotUserData if found, None otherwise
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BotUserDataModel).where(
                    BotUserDataModel.bot_id == self.bot_id,
                    BotUserDataModel.user_id == user_id,
                )
            )
            user_data_model = result.scalar_one_or_none()

            if user_data_model:
                return BotUserData(
                    bot_id=user_data_model.bot_id,
                    user_id=user_data_model.user_id,
                    data=user_data_model.data or {},
                )
            return BotUserData(bot_id=self.bot_id, user_id=user_id, data={})

    async def add_user_data(self, user_data_list: List[BotUserData]) -> None:
        """
        Add or update user data (UPSERT).

        Args:
            user_data_list: List of BotUserData objects
        """
        if not user_data_list:
            return

        async with AsyncSessionLocal() as session:
            for user_data in user_data_list:
                stmt = insert(BotUserDataModel).values(
                    bot_id=self.bot_id, user_id=user_data.user_id, data=user_data.data
                )

                stmt = stmt.on_conflict_do_update(
                    index_elements=["bot_id", "user_id"], set_={"data": user_data.data}
                )

                await session.execute(stmt)

            await session.commit()
            logger.info(
                f"Added/updated {len(user_data_list)} users for bot {self.bot_id}"
            )

    async def replace_user_data(self, user_data_list: List[BotUserData]) -> None:
        """
        Replace all user data for this bot.

        Args:
            user_data_list: List of BotUserData objects
        """
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BotUserDataModel).where(BotUserDataModel.bot_id == self.bot_id)
            )

            if user_data_list:
                for user_data in user_data_list:
                    session.add(
                        BotUserDataModel(
                            bot_id=self.bot_id,
                            user_id=user_data.user_id,
                            data=user_data.data,
                        )
                    )

            await session.commit()
            logger.info(
                f"Replaced all user data for bot {self.bot_id} with {len(user_data_list)} users"
            )

    async def clear_user_data(self) -> None:
        """Clear all user data for this bot."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BotUserDataModel).where(BotUserDataModel.bot_id == self.bot_id)
            )
            await session.commit()
            logger.info(f"Cleared all user data for bot {self.bot_id}")

    async def list_user_data(self) -> List[BotUserData]:
        """
        Get all user data for this bot.

        Returns:
            List of BotUserData objects
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BotUserDataModel).where(BotUserDataModel.bot_id == self.bot_id)
            )
            user_data_models = result.scalars().all()

            return [
                BotUserData(
                    bot_id=model.bot_id, user_id=model.user_id, data=model.data or {}
                )
                for model in user_data_models
            ]

    async def delete_user_data(self, user_id: str) -> None:
        """
        Delete data for a specific user.

        Args:
            user_id: User identifier
        """
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BotUserDataModel).where(
                    BotUserDataModel.bot_id == self.bot_id,
                    BotUserDataModel.user_id == user_id,
                )
            )
            await session.commit()
            logger.info(f"Deleted user {user_id} from bot {self.bot_id}")

    async def create_bot(self, bot_id: UUID) -> None:
        """
        Create bot (no-op for PostgreSQL - table already exists).

        Args:
            bot_id: Bot UUID
        """
        logger.info(f"PostgreSQL create_bot called for {bot_id} (no-op)")

    async def delete_bot_userdata(self, bot_id: UUID) -> None:
        """
        Delete all user data for a bot.

        Args:
            bot_id: Bot UUID
        """
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(BotUserDataModel).where(BotUserDataModel.bot_id == bot_id)
            )
            await session.commit()
            logger.info(f"Deleted all user data for bot {bot_id}")
