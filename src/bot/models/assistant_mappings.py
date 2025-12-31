"""Database model for assistant-to-bot mappings."""

from uuid import uuid4

from sqlalchemy import TIMESTAMP, Column, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from bot.models.chat import Base


class AssistantMapping(Base):
    """Persistent mapping between platform assistant IDs and bot identifiers."""

    __tablename__ = "assistant_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    assistant_id = Column(String(255), nullable=False, index=True)
    bot_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(
        TIMESTAMP,
        nullable=True,
        server_default=func.now(),
    )
    updated_at = Column(
        TIMESTAMP,
        nullable=True,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "assistant_id",
            name="uq_assistant_mappings_assistant_id",
        ),
    )
