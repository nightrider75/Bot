from datetime import datetime
from uuid import UUID as UUIDType
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from bot.deps import AsyncSessionLocal
from bot.models.chat import Base
from bot.types import FileStoreTypes


class ConversationDetails(Base):
    """Fat table for storing all conversation details in one record."""

    __tablename__ = "conversation_details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)  # unique id
    call_id = Column(UUID(as_uuid=True), nullable=False)  # call id - uuid
    session_id = Column(UUID(as_uuid=True), nullable=False)  # session id - uuid
    bot_id = Column(UUID(as_uuid=True), nullable=False)  # bot_id - string
    user_id = Column(String, nullable=False)  # user_id - string
    transcript = Column(
        JSON, nullable=False, default=lambda: []
    )  # json with default empty list
    call_input = Column(
        JSON, nullable=False, default=lambda: {}
    )  # json with default empty dict
    call_output = Column(
        JSON, nullable=False, default=lambda: {}
    )  # json with default empty dict
    start_time = Column(DateTime, nullable=False)  # start time
    end_time = Column(DateTime, nullable=False)  # end time
    call_duration_secs = Column(Integer, nullable=False)  # call duration in seconds
    telephony = Column(String, nullable=False)  # telephony -> non null string
    file_provider = Column(
        String, nullable=True
    )  # storage provider for audio/transcript files (from FileStoreTypes)
    transcript_url = Column(String, nullable=True)  # URL to access the transcript file
    audio_url = Column(String, nullable=True)  # URL to access the audio recording


class ConversationDetailsCreate(BaseModel):
    """Pydantic model for creating conversation details records."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    call_id: UUIDType
    session_id: UUIDType
    bot_id: UUIDType
    user_id: str
    transcript: list = []
    call_input: dict = {}
    call_output: dict = {}
    start_time: datetime
    end_time: datetime
    telephony: str
    file_provider: FileStoreTypes | None = None
    transcript_url: str | None = None
    audio_url: str | None = None

    async def insert(self) -> ConversationDetails:
        """Insert a new conversation details record."""
        async with AsyncSessionLocal() as session:
            # Calculate call duration if not provided
            duration_secs = int((self.end_time - self.start_time).total_seconds())

            conversation_details = ConversationDetails(
                call_id=self.call_id,
                session_id=self.session_id,
                bot_id=self.bot_id,
                user_id=self.user_id,
                transcript=self.transcript,
                call_input=self.call_input,
                call_output=self.call_output,
                start_time=self.start_time,
                end_time=self.end_time,
                call_duration_secs=duration_secs,
                telephony=self.telephony,
                file_provider=self.file_provider,
                transcript_url=self.transcript_url,
                audio_url=self.audio_url,
            )
            session.add(conversation_details)
            await session.commit()
            await session.refresh(conversation_details)
            return conversation_details
