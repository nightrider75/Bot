"""
Bot Hub Config routes.

This module provides API endpoints for managing bot configuration in the bot hub.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bot.bot_hub.hub import BotHub
from bot.types import (
    AgentConfig,
    BotConfig,
    FileStoreConfig,
    PipelineConfig,
    SynthesizerConfig,
    TranscriberConfig,
    TransportConfig,
)

router = APIRouter()


class ConfigResponse(BaseModel):
    """Response model for configuration operations."""

    pipeline_config: PipelineConfig
    tts: SynthesizerConfig
    stt: TranscriberConfig
    llm: AgentConfig
    transport: TransportConfig
    file_store: FileStoreConfig


class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates."""

    pipeline_config: PipelineConfig
    tts: SynthesizerConfig
    stt: TranscriberConfig
    llm: AgentConfig
    transport: TransportConfig
    file_store: FileStoreConfig


@router.get("/{bot_id}/config", response_model=ConfigResponse)
async def get_bot_config(bot_id: UUID):
    """
    Get the configuration for a bot.

    Args:
        bot_id: The identifier for the bot

    Returns:
        ConfigResponse: The bot configuration
    """
    try:
        hub = BotHub(bot_id)
        # Using system user for config access
        config = await hub.config_provider.get_config(bot_id)
        return ConfigResponse(
            pipeline_config=config.pipeline_config,
            tts=config.tts,
            stt=config.stt,
            llm=config.llm,
            transport=config.transport,
            file_store=config.file_store,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get config: {str(e)}"
        ) from e


@router.post("/{bot_id}/config", response_model=ConfigResponse)
async def update_bot_config(bot_id: UUID, request: ConfigUpdateRequest):
    """
    Update the configuration for a bot.

    Args:
        bot_id: The identifier for the bot
        request: The configuration updates to apply

    Returns:
        ConfigResponse: The updated bot configuration
    """
    try:
        hub = BotHub(bot_id)

        await hub.config_provider.set_config(
            bot_id,
            config=BotConfig(
                bot_identifier=bot_id,
                pipeline_config=request.pipeline_config,
                tts=request.tts,
                stt=request.stt,
                llm=request.llm,
                transport=request.transport,
                file_store=request.file_store,
            ),
        )
        config = await hub.config_provider.get_config(bot_id)
        return ConfigResponse(
            pipeline_config=config.pipeline_config,
            tts=config.tts,
            stt=config.stt,
            llm=config.llm,
            transport=config.transport,
            file_store=config.file_store,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get config value: {str(e)}"
        ) from e
