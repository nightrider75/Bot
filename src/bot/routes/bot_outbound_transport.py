import uuid

from fastapi import APIRouter, WebSocket
from loguru import logger
from sqlalchemy import select
from bot_engine.runner.utils import parse_telephony_websocket

from bot.bot_pipeline.runner import run_bot
from bot.config import settings
from bot.deps import AsyncSessionLocal
from bot.models.assistant_mappings import AssistantMapping
from bot.types import StreamConfig, TransportType

router = APIRouter()


async def _fetch_mapping_by_assistant_id(assistant_id: str) -> AssistantMapping | None:
    async with AsyncSessionLocal() as session:
        stmt = select(AssistantMapping).where(
            AssistantMapping.assistant_id == assistant_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def _resolve_bot_identifier(assistant_id: str | None):
    """Translate the assistant_id query arg to a bot UUID or close the socket."""
    if not assistant_id:
        return None

    mapping = await _fetch_mapping_by_assistant_id(assistant_id)
    if not mapping:
        return None

    return mapping.bot_id


@router.websocket("/plivo/ws")
async def plivo_websocket_endpoint(websocket: WebSocket):
    # Log query parameters from the WebSocket connection URL
    query_params = dict(websocket.query_params)
    logger.info(f"Plivo WebSocket query parameters: {query_params}")
    await websocket.accept()
    assistant_id = query_params.get("assistant_id")
    bot_id = await _resolve_bot_identifier(assistant_id)
    if bot_id is None:
        logger.error("No assistant mapping found for assistant_id=%s", assistant_id)
        await websocket.close(
            code=1008,
            reason="assistant_id is not mapped to a bot identifier; configure it in the platform UI.",
        )
        return
    session_id = uuid.uuid4()
    with logger.contextualize(bot_id=bot_id, session_id=session_id, telephony="plivo"):
        telephony, call_data = await parse_telephony_websocket(websocket)
        logger.debug(
            f"Received Plivo WebSocket connection provider: {telephony} : {call_data}"
        )
        stream_config = StreamConfig(
            stream_id=call_data.get("stream_id"),
            call_id=call_data.get("call_id"),
            account_id=call_data.get("body", {}).get("account_sid"),
            user_id=call_data.get("body", {}).get("user_id"),
            outbound_encoding="PCMU",
            bot_session_id=session_id,
            host_id=settings.host_id,
            bot_assistant_id=assistant_id,
        )
        with logger.contextualize(
            stream_id=stream_config.stream_id,
            call_id=stream_config.call_id,
            account_id=stream_config.account_id,
        ):
            await run_bot(
                transport_type=TransportType.PLIVO,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
                extra_user_data=query_params,
            )


# TWILIO INTEGRATION


@router.websocket("/twilio/ws")
async def twilio_websocket_endpoint(websocket: WebSocket):
    # Log query parameters from the WebSocket connection URL
    query_params = dict(websocket.query_params)
    logger.info(f"Twilio WebSocket query parameters: {query_params}")
    await websocket.accept()
    assistant_id = query_params.get("assistant_id")
    bot_id = await _resolve_bot_identifier(assistant_id)
    if bot_id is None:
        logger.error("No assistant mapping found for assistant_id=%s", assistant_id)
        await websocket.close(
            code=1008,
            reason="assistant_id is not mapped to a bot identifier; configure it in the platform UI.",
        )
        return
    session_id = uuid.uuid4()
    with logger.contextualize(bot_id=bot_id, session_id=session_id, telephony="twilio"):
        telephony, call_data = await parse_telephony_websocket(websocket)
        logger.debug(
            f"Received Twilio WebSocket connection provider: {telephony} : {call_data}"
        )
        stream_config = StreamConfig(
            stream_id=call_data.get("stream_id"),
            call_id=call_data.get("call_id"),
            account_id=call_data.get("body", {}).get("account_sid"),
            user_id=call_data.get("body", {}).get("user_id"),
            outbound_encoding="PCMU",
            bot_session_id=session_id,
            host_id=settings.host_id,
            bot_assistant_id=assistant_id,
        )
        with logger.contextualize(
            stream_id=stream_config.stream_id,
            call_id=stream_config.call_id,
            account_id=stream_config.account_id,
        ):
            await run_bot(
                transport_type=TransportType.TWILIO,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
                extra_user_data=query_params,
            )
