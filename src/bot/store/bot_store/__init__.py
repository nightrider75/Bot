"""Bot store implementations.

This module provides access to different bot store backend implementations
including Firestore and PostgreSQL.
"""

from bot.store.bot_store.firestore import FireStoreBotStore
from bot.store.bot_store.interface import BotStoreInterface

__all__ = ["BotStoreInterface", "FireStoreBotStore"]
