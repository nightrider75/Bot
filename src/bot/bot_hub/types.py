"""
Bot Hub provider type enums for the bot orchestration system.

This module defines enums that specify which provider classes should be used
for different provider types in the bot hub system.
"""

from enum import StrEnum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from bot.bot_hub.functions.types import FunctionInstance


class ConfigProviderType(StrEnum):
    """Enum for configuration provider types."""

    DEFAULT_SETTINGS = "default_settings"
    LOCAL_FILE = "local_file"
    POSTGRESQL = "postgresql"


class FunctionsProviderType(StrEnum):
    """Enum for functions provider types."""

    EMPTY = "empty"
    EMBEDDED = "embedded"


class NodeProviderType(StrEnum):
    """Enum for prompt provider types."""

    LOCAL_FILE = "local_file"
    DB_FIRESTORE = "db_firestore"
    POSTGRESQL = "postgresql"


class UserDataProviderType(StrEnum):
    """Enum for user data provider types."""

    LOCAL_CSV = "local_csv"
    IN_MEMORY = "in_memory"
    POSTGRESQL = "postgresql"


class BotProviderType(StrEnum):
    """Enum for bot provider types."""

    LOCAL_FILE = "local_file"
    POSTGRESQL = "postgresql"


class Bot(BaseModel):
    """
    Represents a Bot within the platform
    """

    id: UUID
    name: str
    initial_node_id: Optional[UUID] = None


class BotNodeMeta(BaseModel):
    """
    Represents a bot node with its associated prompt content.
    """

    bot_id: UUID
    node_id: UUID
    node_name: str


class BotNode(BotNodeMeta):
    """
    Represents a bot node with its associated prompt content.
    """

    node_name: str
    prompt: str
    functions: List[FunctionInstance] = list()


class BotUserData(BaseModel):
    user_id: str
    data: Dict[str, Any] = {}
