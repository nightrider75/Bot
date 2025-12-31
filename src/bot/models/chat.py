from datetime import datetime
from enum import StrEnum
from uuid import UUID as UUIDType
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

from bot.deps import AsyncSessionLocal

Base = declarative_base()


class ChatConversationStatus(StrEnum):
    RECEIVED = "received"
    ACTIVE = "active"
    CLOSED = "closed"


class ChatCloseReason(StrEnum):
    USER_IDLE = "user_idle"
    USER_DISCONNECTED = "user_disconnected"
    CALL_TRANSFERRED = "call_transferred"
    CALL_END_PHRASE_TRIGGERED = "call_end_phrase_triggered"
    PIPELINE_TTL_TRIGGERED = "pipeline_ttl_triggered"
    OTHER = "other"


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    transcript_path = Column(String, nullable=True)
    recording_audio_path = Column(String, nullable=True)
    call_id = Column(String, nullable=True)
    user_id = Column(String, nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    host_id = Column(String, nullable=False)
    bot_identifier = Column(UUID(as_uuid=True), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    call_duration_secs = Column(Integer, nullable=True)
    status = Column(
        SQLEnum(ChatConversationStatus),
        nullable=False,
        default=ChatConversationStatus.RECEIVED,
    )
    closed_reason = Column(
        SQLEnum(ChatCloseReason), nullable=False, default=ChatCloseReason.OTHER
    )
    chat_extra_data = Column(JSON, default=dict)

    async def mark_active(self) -> "ChatConversation":
        try:
            async with AsyncSessionLocal() as session:
                self.status = ChatConversationStatus.ACTIVE
                session.add(self)
                await session.commit()
                await session.refresh(self)
                return self
        except Exception as e:
            logger.error(
                f"Failed to mark conversation as active for session {self.session_id}: {e}"
            )
            return None

    async def close_conversation(
        self,
        close_reason: ChatCloseReason,
        extra_data: dict | None = None,
        transcript_path: str | None = None,
        recording_audio_path: str | None = None,
        call_end_time: datetime | None = None,
    ) -> "ChatConversation":
        try:
            async with AsyncSessionLocal() as session:
                self.closed_reason = close_reason
                self.status = ChatConversationStatus.CLOSED
                self.end_time = call_end_time or datetime.utcnow()
                self.call_duration_secs = int(
                    (self.end_time - self.start_time).total_seconds()
                )
                if transcript_path:
                    self.transcript_path = transcript_path
                if recording_audio_path:
                    self.recording_audio_path = recording_audio_path
                if extra_data:
                    self.chat_extra_data.update(extra_data)
                session.add(self)
                await session.commit()
                await session.refresh(self)
                return self
        except Exception as e:
            logger.error(
                f"Failed to close conversation for session {self.session_id}: {e}"
            )
            return None


class ChatConversationCreate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    session_id: UUIDType
    bot_identifier: UUIDType
    host_id: str
    call_id: str | None = None

    async def insert(self) -> ChatConversation | None:
        # TEMP: Skip database persistence for chat conversations.
        # This returns an in-memory stub that mimics the real ChatConversation API
        # so the rest of the pipeline can continue without a backing database.
        class _InMemoryChatConversation:
            def __init__(self, create: "ChatConversationCreate"):
                self.id = uuid4()
                self.user_id = create.user_id
                self.session_id = create.session_id
                self.bot_identifier = create.bot_identifier
                self.call_id = create.call_id
                self.host_id = create.host_id
                self.start_time = datetime.utcnow()
                self.status = ChatConversationStatus.RECEIVED

            async def mark_active(self):
                self.status = ChatConversationStatus.ACTIVE
                return self

            async def close_conversation(
                self,
                close_reason: ChatCloseReason,
                extra_data: dict | None = None,
                transcript_path: str | None = None,
                recording_audio_path: str | None = None,
                call_end_time: datetime | None = None,
            ):
                self.closed_reason = close_reason
                self.status = ChatConversationStatus.CLOSED
                self.end_time = call_end_time or datetime.utcnow()
                self.call_duration_secs = int(
                    (self.end_time - self.start_time).total_seconds()
                )
                if transcript_path:
                    self.transcript_path = transcript_path
                if recording_audio_path:
                    self.recording_audio_path = recording_audio_path
                if extra_data:
                    self.chat_extra_data = extra_data
                return self

        logger.warning(
            "Chat persistence is temporarily disabled; returning in-memory conversation stub."
        )
        return _InMemoryChatConversation(self)


class ChatConversationUpdate(BaseModel):
    transcript_path: str | None = None
    recording_audio_path: str | None = None
    call_id: str | None = None
    end_time: datetime | None = None
    call_duration_secs: int | None = None
    status: ChatConversationStatus | None = None
    closed_reason: ChatCloseReason | None = None
    chat_extra_data: dict | None = None


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    content = Column(String, nullable=False)
    role = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_conversations.id"), nullable=False
    )
    bot_identifier = Column(UUID(as_uuid=True), nullable=False)
    chat_extra_data = Column(JSON, default=dict)


class ChatMessageNew(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: str
    role: str
    conversation_id: UUIDType
    bot_identifier: UUIDType
    chat_message_extra_data: dict | None = {}

    async def insert(self) -> ChatMessage | None:
        try:
            async with AsyncSessionLocal() as session:
                chat_message = ChatMessage(
                    content=self.content,
                    role=self.role,
                    conversation_id=self.conversation_id,
                    bot_identifier=self.bot_identifier,
                    chat_extra_data=self.chat_message_extra_data or {},
                    timestamp=datetime.utcnow(),
                )
                session.add(chat_message)
                await session.commit()
                await session.refresh(chat_message)
                return chat_message
        except Exception as e:
            logger.error(
                f"Failed to insert chat message for conversation {self.conversation_id}: {e}"
            )
            return None
