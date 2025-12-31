"""SQLAlchemy models for PostgreSQL bot storage.

This module defines the database models for storing bot metadata and configuration.
Following the same pattern as existing chat.py models with shared Base.
"""

from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import TIMESTAMP, Column, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from bot.models.chat import Base


class Bot(Base):
    """Bot metadata table.

    Stores bot identification and starting node configuration.
    Each bot has a unique bot_id and a start_node_id that points to
    the initial node for conversations.
    """

    __tablename__ = "bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bot_name = Column(String(255), nullable=False)
    start_node_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Config(Base):
    """Bot configuration table.

    Stores bot configuration as JSONB for flexibility.
    Each config is tied to exactly one bot via foreign key with CASCADE delete.
    """

    __tablename__ = "config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bot_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )
    config = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Node(Base):
    """Nodes table - conversation states.

    Based on official db.md structure:
    - id (nodeid) as primary key
    - botid (no foreign key constraint per PR #1 feedback)
    - prompt for conversation state
    - timestamps

    The node_id is a UUID (matching bots.start_node_id type).
    """

    __tablename__ = "nodes"

    # Per db.md: "id (nodeid)" - node_id IS the primary key (UUID type)
    node_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    node_name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class FunctionMapping(Base):
    """FunctionMappings table - functions assigned to nodes.

    Based on official db.md structure:
    - Stores which functions are available at each conversation state (node)
    - Separated from nodes table for clean architecture
    - Includes transition rules and pre-say configuration
    - All ID columns use UUID type for consistency
    """

    __tablename__ = "function_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    node_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    function_id = Column(String(255), nullable=False, index=True)
    function_label = Column(String(255), nullable=False, index=False)
    function_provider_id = Column(String(255), nullable=True, default="embedded")
    transition_mappings = Column(
        JSONB, nullable=False, server_default=func.text("'{}'::jsonb")
    )
    pre_say_config = Column(
        JSONB, nullable=False, server_default=func.text("'{}'::jsonb")
    )
    ack_llm_description = Column(String(255), nullable=True, index=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class BotUserData(Base):
    """Bot user data table - user session information.

    Stores user session data with UPSERT pattern (INSERT or UPDATE).
    Each bot can have multiple users, each user has one data record.
    """

    __tablename__ = "bot_user_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    bot_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    data = Column(JSONB, nullable=False, server_default=func.text("'{}'::jsonb"))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        sa.UniqueConstraint("bot_id", "user_id", name="uq_bot_user_data"),
    )
