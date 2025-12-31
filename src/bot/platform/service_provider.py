from typing import List
from uuid import UUID

from pydantic import BaseModel

from bot.bot_hub.functions.types import BotFunction
from bot.bot_hub.types import FunctionsProviderType
from bot.types import LLMType, SynthesizerType, TranscriberType


class ServiceMeta(BaseModel):
    id: UUID
    name: str
    description: str


class AgentService(ServiceMeta):
    provider: LLMType
    model: str | None = None
    api_key: str | None = None
    endpoint: str | None = None


class TranscriberService(ServiceMeta):
    provider: TranscriberType
    model: str | None = None
    api_key: str | None = None
    credentials_path: str | None = None
    region: str | None = None
    endpoint: str | None = None


class SynthesizerService(ServiceMeta):
    provider: SynthesizerType
    model: str | None = None
    api_key: str | None = None
    region: str | None = None
    credentials_path: str | None = None


class ToolCallService(ServiceMeta):
    provider: FunctionsProviderType
    base_url: str | None = None


class ServiceProvider:
    @staticmethod
    def get_function_providers() -> List[ServiceMeta]:
        pass

    @staticmethod
    def list_functions(function_provider: UUID) -> List[BotFunction]:
        pass

    @staticmethod
    def list_agents() -> List[ServiceMeta]:
        pass

    @staticmethod
    def list_transcriber() -> List[ServiceMeta]:
        pass

    @staticmethod
    def list_synthesizer() -> List[ServiceMeta]:
        pass

    @staticmethod
    def get_agent_service(agent_id: UUID) -> AgentService:
        pass

    @staticmethod
    def get_transcriber_service(service_id: UUID) -> TranscriberService:
        pass

    @staticmethod
    def get_synthesizer_service(service_id: UUID) -> SynthesizerService:
        pass
