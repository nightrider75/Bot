"""
Fast WebSocket endpoint for Avexi.ai landing page demo agents.

This module provides a high-performance WebSocket endpoint optimized for 
real-time audio streaming for the demo agents on the Avexi.ai landing page.
Supports multilingual AI agents (English US/UK/Indian/UAE, Hindi, German, French, Spanish).

Audio Configuration (aligned with frontend):
- Input Sample Rate: 16000 Hz (16 kHz) for STT compatibility
- Output Sample Rate: 24000 Hz (24 kHz) for TTS quality  
- Bit Depth: 16-bit PCM (Linear16)
- Channels: Mono (1 channel)
- Frame Format: 8-byte header (uint32 sampleRate LE + uint32 channels LE) + PCM16LE data
"""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger
from pydantic import BaseModel

from bot.bot_pipeline.runner import run_bot
from bot.config import settings
from bot.types import StreamConfig, TransportType


router = APIRouter(prefix="/demo", tags=["Demo WebSocket"])


# Audio configuration constants - aligned with frontend
DEMO_INPUT_SAMPLE_RATE = 16000   # 16 kHz for STT (matches frontend mic capture)
DEMO_OUTPUT_SAMPLE_RATE = 24000  # 24 kHz for TTS output
DEMO_CHANNELS = 1                # Mono
DEMO_BIT_DEPTH = 16              # 16-bit PCM
DEMO_FRAME_SIZE = 1024           # Samples per frame


class DemoSessionConfig(BaseModel):
    """Configuration for a demo WebSocket session."""
    bot_id: UUID
    language: Optional[str] = "en-US"
    voice_id: Optional[str] = None
    user_id: Optional[str] = "demo_user"
    industry: Optional[str] = None


# Language code to voice/language mapping for demo agents
# Maps frontend language IDs to backend language codes
DEMO_LANGUAGE_CONFIGS = {
    # Global English variants (frontend uses: us, uk, in, uae)
    "en-US": {"name": "English (US)", "native": "English", "frontend_id": "us"},
    "en-GB": {"name": "English (UK)", "native": "English", "frontend_id": "uk"},
    "en-IN": {"name": "English (India)", "native": "English", "frontend_id": "in"},
    "en-AU": {"name": "English (Australia)", "native": "English", "frontend_id": "au"},
    
    # Multilingual variants (frontend uses: hi, de, fr, es)
    "hi": {"name": "Hindi", "native": "हिन्दी", "frontend_id": "hi"},
    "de": {"name": "German", "native": "Deutsch", "frontend_id": "de"},
    "fr": {"name": "French", "native": "Français", "frontend_id": "fr"},
    "es": {"name": "Spanish", "native": "Español", "frontend_id": "es"},
}

# Bot personas mapped to industry types (matches frontend BOT_PERSONAS)
BOT_PERSONAS = {
    "hospitality": "4572cdf4-a104-4a59-a93e-3594e567c4bb",
    "sales": "fc8bc2f3-cf22-4341-9d3c-773fd8637f03",
    "outbound": "3bf62ab4-ace3-42e8-8318-ccb712f91554",
    "companion": "a7590a4c-6277-48ec-b36d-f7c6cd48707d",
    "support": "7b6da7fa-de62-4aaa-8d8b-a10d8c09b18f",
}


@router.websocket("/ws/{bot_id}")
async def demo_websocket_endpoint(
    websocket: WebSocket,
    bot_id: UUID,
    language: Optional[str] = Query(default="en-US", description="Language code (en-US, en-GB, en-IN, hi, de, fr, es)"),
    voice_id: Optional[str] = Query(default=None, description="TTS voice ID override"),
    user_id: Optional[str] = Query(default="demo_user", description="User identifier"),
    industry: Optional[str] = Query(default=None, description="Industry context (hospitality, sales, outbound, companion, support)"),
):
    """
    High-performance WebSocket endpoint for Avexi.ai landing page demo agents.
    
    Optimized for real-time audio streaming with low latency.
    
    ## Connection URL Format
    ```
    wss://api.avexi.ai/api/v1/demo/ws/{bot_id}?language=en-US&user_id=demo_user&voice_id=xxx
    ```
    
    ## Query Parameters
    - **bot_id** (required): UUID of the bot to connect to
    - **language** (optional): Language code for the agent. Default: "en-US"
      - English: en-US, en-GB, en-IN, en-AU
      - Multilingual: hi (Hindi), de (German), fr (French), es (Spanish)
    - **voice_id** (optional): TTS voice ID override for accent
    - **user_id** (optional): User identifier for session tracking
    - **industry** (optional): Industry context for the demo
    
    ## Audio Protocol (Binary Frames)
    All audio frames have an 8-byte header followed by PCM16LE audio data:
    - Bytes 0-3: uint32 sampleRate (little-endian)
    - Bytes 4-7: uint32 channels (little-endian)  
    - Bytes 8+: PCM16LE audio samples
    
    - **Inbound (Client → Server)**: 8-byte header + PCM16LE @ 16kHz mono
    - **Outbound (Server → Client)**: 8-byte header + PCM16LE @ 24kHz mono
    
    ## JSON Messages
    Server may send JSON messages for state updates:
    - `{"type": "bot_ready"}` - Bot is ready to receive audio
    - `{"type": "listening"}` - Bot is listening for speech
    - `{"type": "processing"}` - Bot is processing/thinking
    - `{"type": "speaking"}` - Bot is speaking (audio frames follow)
    """
    
    # Accept WebSocket connection immediately for fast connection
    await websocket.accept()
    
    session_id = uuid4()
    
    # Resolve language configuration
    lang_config = DEMO_LANGUAGE_CONFIGS.get(language, DEMO_LANGUAGE_CONFIGS["en-US"])
    
    with logger.contextualize(
        bot_id=bot_id,
        session_id=session_id,
        transport="demo_websocket",
        language=language,
        industry=industry,
        voice_id=voice_id,
    ):
        logger.info(
            f"Demo WebSocket connection established | "
            f"Language: {lang_config['name']} | "
            f"Industry: {industry or 'general'} | "
            f"Voice ID: {voice_id or 'default'}"
        )
        
        try:
            # Create optimized stream configuration for demo
            stream_config = StreamConfig(
                stream_id=f"demo_ws_{session_id}",
                call_id=f"demo_call_{session_id}",
                account_id="avexi_demo",
                outbound_encoding="PCM",  # Use PCM for WebSocket
                user_id=user_id or "demo_user",
                bot_session_id=session_id,
                host_id=settings.host_id or "demo_host",
            )
            
            # Run the bot with optimized WebSocket transport
            await run_bot(
                transport_type=TransportType.BOT_WEBSOCKET,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
                voice_id_override=voice_id,
                language_override=language,
            )
            
        except WebSocketDisconnect:
            logger.info(f"Demo WebSocket disconnected normally | session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error in demo WebSocket endpoint: {str(e)}")
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except Exception:
                pass  # Connection may already be closed


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported languages for demo agents.
    
    Returns language codes and display names for frontend language selector.
    """
    return {
        "languages": [
            {"code": code, "name": config["name"], "native": config["native"]}
            for code, config in DEMO_LANGUAGE_CONFIGS.items()
        ],
        "default": "en-US",
    }


@router.get("/audio-config")
async def get_audio_config():
    """
    Get audio configuration for demo WebSocket connection.
    
    Frontend should use these settings for audio capture and playback.
    """
    return {
        "input_sample_rate": DEMO_INPUT_SAMPLE_RATE,
        "output_sample_rate": DEMO_OUTPUT_SAMPLE_RATE,
        "channels": DEMO_CHANNELS,
        "bit_depth": DEMO_BIT_DEPTH,
        "frame_size": DEMO_FRAME_SIZE,
        "encoding": "linear16",
        "header_size_bytes": 8,
        "frame_duration_ms": round((DEMO_FRAME_SIZE / DEMO_INPUT_SAMPLE_RATE) * 1000, 2),
    }


@router.get("/industries")
async def get_supported_industries():
    """
    Get list of supported industry categories for demo agents.
    """
    return {
        "industries": [
            {"id": "hospitality", "name": "Hospitality", "description": "Hotel booking, restaurant reservations"},
            {"id": "sales", "name": "Sales", "description": "Product inquiries, sales assistance"},
            {"id": "outbound", "name": "Outbound", "description": "Proactive customer outreach"},
            {"id": "companion", "name": "Companion", "description": "Conversational AI companion"},
            {"id": "support", "name": "Support", "description": "Customer support and help desk"},
        ]
    }
