from bot_engine.services.azure.llm import AzureLLMService
from bot_engine.services.fireworks.llm import FireworksLLMService
from bot_engine.services.groq.llm import GroqLLMService
from bot_engine.services.openai.base_llm import BaseOpenAILLMService
from bot_engine.services.openai.llm import OpenAILLMService

from bot.config import (
    DEFAULT_AZURE_MODEL,
    DEFAULT_FIREWORKS_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENAI_MODEL,
)
from bot.types import AgentConfig, LLMType


class LLMProvider:
    @classmethod
    def get_provider(cls, llm_config: AgentConfig):
        if llm_config.provider == LLMType.OPENAI:
            return OpenAILLMService(
                api_key=llm_config.api_key,
                model=llm_config.model or DEFAULT_OPENAI_MODEL,
                params=BaseOpenAILLMService.InputParams(service_tier="priority"),
            )
        elif llm_config.provider == LLMType.GOOGLE:
            raise NotImplementedError("Google provider not implemented yet")
        elif llm_config.provider == LLMType.ANTHROPIC:
            raise NotImplementedError("Anthropic provider not implemented yet")
        elif llm_config.provider == LLMType.AZUREOPENAI:
            return AzureLLMService(
                api_key=llm_config.api_key,
                endpoint=llm_config.endpoint,
                model=llm_config.model or DEFAULT_AZURE_MODEL,
            )
        elif llm_config.provider == LLMType.CEREBRAS:
            raise NotImplementedError("Cerebras provider not implemented yet")
        elif llm_config.provider == LLMType.FIREWORKS:
            return FireworksLLMService(
                api_key=llm_config.api_key,
                model=llm_config.model or DEFAULT_FIREWORKS_MODEL,
            )
        elif llm_config.provider == LLMType.GROQ:
            return GroqLLMService(
                api_key=llm_config.api_key,
                model=llm_config.model or DEFAULT_GROQ_MODEL,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {llm_config.provider}")
