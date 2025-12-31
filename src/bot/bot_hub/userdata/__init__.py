"""
User data provider module initialization.
"""

from bot.bot_hub.userdata.base import LocalCSVUserDataProvider
from bot.bot_hub.userdata.interface import UserDataInterface
from bot.bot_hub.userdata.memory import InMemoryUserDataProvider
from bot.bot_hub.userdata.postgresql import (
    PostgreSQLUserDataProvider,
)

__all__ = [
    "UserDataInterface",
    "LocalCSVUserDataProvider",
    "InMemoryUserDataProvider",
    "PostgreSQLUserDataProvider",
]
