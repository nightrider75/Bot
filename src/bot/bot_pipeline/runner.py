import io
import os
import wave
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import aiofiles
import nltk
from fastapi import WebSocket
from loguru import logger
from pydub import AudioSegment
from bot_engine.frames.frames import (
    EndFrame,
    TranscriptionUpdateFrame,
)

from bot.bot_hub.hub import BotSession
from bot.bot_pipeline.pipeline import BotPipeline
from bot.models.chat import (
    ChatCloseReason,
    ChatConversationCreate,
    ChatMessageNew,
)
from bot.types import (
    StreamConfig,
    TransportType,
)

# Language code to full name mapping for multilingual support
# Includes pre-configured greetings for instant response (no LLM delay)
LANGUAGE_MAP = {
    # English Accents/Variations
    "en-US": {
        "name": "US English",
        "native": "English (US)",
        "stt_code": "en-US",
        "greetings": {
            "hospitality": "Hello! Welcome to our hotel. How can I assist you today?",
            "sales_outbound": "Hi there! This is a quick call to share some exciting opportunities with you. Do you have a moment?",
            "sales_inbound": "Hi! Welcome to our sales line. How can I assist you today?",
            "companion": "Hey there! It's nice to hear from you. What's on your mind today?",
            "customer_support": "Hello! Thank you for contacting customer support. How can I help you today?",
        },
    },
    "en-GB": {
        "name": "UK English",
        "native": "English (UK)",
        "stt_code": "en-GB",
        "greetings": {
            "hospitality": "Good day! Welcome to our hotel. How may I assist you today?",
            "sales_outbound": "Hello! I'm calling to share some wonderful opportunities with you. Do you have a moment to chat?",
            "sales_inbound": "Hello! Welcome to our sales line. How may I help you today?",
            "companion": "Hello there! Lovely to hear from you. What would you like to talk about today?",
            "customer_support": "Good day! Thank you for contacting customer support. How may I assist you today?",
        },
    },
    "en-IN": {
        "name": "Indian English",
        "native": "English (India)",
        "stt_code": "en-IN",
        "greetings": {
            "hospitality": "Namaste! Welcome to our hotel. How can I help you today?",
            "sales_outbound": "Hello! I'm calling to share some exciting opportunities with you. Do you have a moment?",
            "sales_inbound": "Hello! Welcome to our sales line. How can I assist you today?",
            "companion": "Hello! Nice to hear from you. What would you like to discuss today?",
            "customer_support": "Hello! Thank you for contacting customer support. How may I help you today?",
        },
    },
    "en-AE": {
        "name": "UAE English",
        "native": "English (UAE)",
        "stt_code": "en",
        "greetings": {
            "hospitality": "Welcome! Thank you for choosing our hotel. How may I assist you today?",
            "sales_outbound": "Hello! I'm reaching out to share some exciting opportunities with you. Do you have a moment?",
            "sales_inbound": "Welcome! How can I assist you with our services today?",
            "companion": "Hello! Great to hear from you. What's on your mind today?",
            "customer_support": "Welcome! Thank you for contacting customer support. How can I help you today?",
        },
    },
    # Multilingual Languages
    "hi": {
        "name": "Hindi",
        "native": "हिंदी",
        "stt_code": "hi",
        "greetings": {
            "hospitality": "नमस्ते! हमारे होटल में आपका स्वागत है। आज मैं आपकी कैसे सहायता कर सकता हूं?",
            "sales_outbound": "नमस्ते! मैं आपके साथ कुछ रोमांचक अवसर साझा करने के लिए कॉल कर रहा हूं। क्या आपके पास एक क्षण है?",
            "sales_inbound": "नमस्ते! हमारी सेल्स लाइन में आपका स्वागत है। आज मैं आपकी कैसे सहायता कर सकता हूं?",
            "companion": "नमस्ते! आपसे बात करके अच्छा लग रहा है। आज आपके मन में क्या है?",
            "customer_support": "नमस्ते! ग्राहक सहायता से संपर्क करने के लिए धन्यवाद। मैं आज आपकी कैसे मदद कर सकता हूं?",
        },
    },
    "de": {
        "name": "German",
        "native": "Deutsch",
        "stt_code": "de",
        "greetings": {
            "hospitality": "Guten Tag! Willkommen in unserem Hotel. Wie kann ich Ihnen heute helfen?",
            "sales_outbound": "Hallo! Ich rufe an, um einige spannende Möglichkeiten mit Ihnen zu teilen. Haben Sie einen Moment Zeit?",
            "sales_inbound": "Hallo! Willkommen bei unserer Verkaufsabteilung. Wie kann ich Ihnen heute helfen?",
            "companion": "Hallo! Schön, von Ihnen zu hören. Worüber möchten Sie heute sprechen?",
            "customer_support": "Guten Tag! Vielen Dank, dass Sie den Kundensupport kontaktiert haben. Wie kann ich Ihnen heute helfen?",
        },
    },
    "fr": {
        "name": "French",
        "native": "Français",
        "stt_code": "fr",
        "greetings": {
            "hospitality": "Bonjour! Bienvenue dans notre hôtel. Comment puis-je vous aider aujourd'hui?",
            "sales_outbound": "Bonjour! J'appelle pour partager avec vous quelques opportunités passionnantes. Avez-vous un moment?",
            "sales_inbound": "Bonjour! Bienvenue sur notre ligne de vente. Comment puis-je vous aider aujourd'hui?",
            "companion": "Bonjour! Ravi d'avoir de vos nouvelles. De quoi aimeriez-vous parler aujourd'hui?",
            "customer_support": "Bonjour! Merci de contacter le support client. Comment puis-je vous aider aujourd'hui?",
        },
    },
    "es": {
        "name": "Spanish",
        "native": "Español",
        "stt_code": "es",
        "greetings": {
            "hospitality": "¡Hola! Bienvenido a nuestro hotel. ¿Cómo puedo ayudarte hoy?",
            "sales_outbound": "¡Hola! Llamo para compartir algunas oportunidades emocionantes contigo. ¿Tienes un momento?",
            "sales_inbound": "¡Hola! Bienvenido a nuestra línea de ventas. ¿Cómo puedo ayudarte hoy?",
            "companion": "¡Hola! Me alegro de saber de ti. ¿De qué te gustaría hablar hoy?",
            "customer_support": "¡Hola! Gracias por contactar con el soporte al cliente. ¿Cómo puedo ayudarte hoy?",
        },
    },
    # Legacy mappings for backward compatibility
    "it": {"name": "Italian", "native": "Italiano", "stt_code": "it"},
    "ar": {"name": "Arabic", "native": "العربية", "stt_code": "ar"},
}


async def run_bot(
    transport_type: TransportType,
    stream_config: StreamConfig,
    connection: WebSocket | Any,
    bot_identifier: UUID,
    extra_user_data: Dict[str, str] = dict(),
    voice_id_override: Optional[str] = None,
    language_override: Optional[str] = None,
):
    logger.info(
        f"Starting bot run with transport_type: {transport_type}, bot_identifier: {bot_identifier}"
    )
    logger.debug(f"Stream config: {stream_config}")

    # Initialize Bot instance
    logger.debug(f"Creating Bot instance with bot_identifier: {bot_identifier}")
    bot = BotSession(
        bot_id=bot_identifier,
        user_id=stream_config.user_id,
        transport_type=transport_type,
    )
    logger.info(f"Initializing bot {bot_identifier}")
    await bot.initialize()
    logger.debug(f"Bot initialization completed for {bot_identifier}")

    logger.debug(
        f"Creating chat conversation object for user_id: {stream_config.user_id}, session_id: {stream_config.bot_session_id}"
    )
    chat_conversation_obj = ChatConversationCreate(
        user_id=stream_config.user_id,
        session_id=stream_config.bot_session_id,
        bot_identifier=bot_identifier,
        call_id=stream_config.call_id,
        host_id=stream_config.host_id,
    )
    chat_conversation = await chat_conversation_obj.insert()
    if not chat_conversation:
        logger.error("Failed to create chat conversation in the database.")
        return
    chat_closed_reason = ChatCloseReason.OTHER
    logger.debug(
        f"Created chat conversation with ID: {chat_conversation.id} for user: {chat_conversation.user_id}"
    )

    # Get configurations from Bot instance
    logger.info(f"Retrieving configurations from Bot session instance {bot_identifier}")

    logger.info("Creating bot configuration")
    bot_config = await bot.get_config()
    logger.debug("Bot configuration created successfully")

    # Apply voice_id override if provided (for accent selection)
    if voice_id_override:
        logger.info(f"Applying voice_id override: {voice_id_override}")
        bot_config.tts.voice_id = voice_id_override

    # Apply language override if provided (for multilingual support)
    language_info = None
    if language_override and language_override in LANGUAGE_MAP:
        language_info = LANGUAGE_MAP[language_override]
        logger.info(
            f"Applying language override: {language_override} ({language_info['name']})"
        )
        # Override STT language for proper transcription
        bot_config.stt.language = [language_info["stt_code"]]
        # Override TTS language
        bot_config.tts.language = language_info["stt_code"]
        
        # Set pre-configured greeting for instant response (no LLM delay)
        if bot_config.pipeline_config and "greetings" in language_info:
            # Get bot name from bot provider
            bot_data = await bot.bot_hub.bot_provider.get_bot(bot_identifier)
            bot_name = bot_data.name
            if bot_name in language_info["greetings"]:
                greeting = language_info["greetings"][bot_name]
                bot_config.pipeline_config.initial_audio_phrase = greeting
                bot_config.pipeline_config.initial_audio_id = None
                logger.info(
                    f"Set pre-configured greeting for {bot_name} in {language_info['name']}: {greeting}"
                )
            else:
                # Fallback: disable greeting if bot type not found
                bot_config.pipeline_config.initial_audio_phrase = None
                bot_config.pipeline_config.initial_audio_id = None
                logger.warning(
                    f"No pre-configured greeting found for bot '{bot_name}' in {language_info['name']}"
                )
        logger.debug(
            f"STT language set to: {bot_config.stt.language}, TTS language set to: {bot_config.tts.language}"
        )

    logger.info("Initializing bot pipeline")
    bot_pipeline = BotPipeline(
        config=bot_config,
        stream_config=stream_config,
        connection=connection,
    )
    logger.debug(f"Initialized bot pipeline with config: {bot_config}")

    bot_pipeline.flow_manager.state["user_data"] = bot.get_user_data()
    bot_pipeline.flow_manager.state["extra_user_data"] = extra_user_data
    bot_pipeline.flow_manager.state["stream_config"] = stream_config.model_dump_json()

    audio_path = None
    transcript_path = None
    call_start_time = None
    call_end_time = None
    call_transcript_data = []

    @bot_pipeline.task.event_handler("on_pipeline_started")
    async def on_pipeline_started(_task, _frame: Any):
        nonlocal call_transcript_data
        logger.info("Pipeline has started and is ready to process frames.")

    @bot_pipeline.event_handler("user_idle_disconnect")
    async def handle_user_idle_disconnect(bot_pipeline):
        nonlocal chat_closed_reason
        chat_closed_reason = ChatCloseReason.USER_IDLE
        logger.debug("UserIdle disconnect triggered")
        await bot_pipeline.task.queue_frame(EndFrame())

    @bot_pipeline.task.event_handler("on_max_ttl_timeout")
    async def on_max_ttl_timeout(_task):
        logger.warning("Pipeline max TTL exceeded")
        nonlocal chat_closed_reason
        chat_closed_reason = ChatCloseReason.PIPELINE_TTL_TRIGGERED
        logger.debug("UserIdle disconnect triggered")

    @bot_pipeline.transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client):
        nonlocal call_start_time, call_transcript_data
        logger.info(
            f"Client connected for bot {bot_identifier}, initializing flow manager"
        )
        call_start_time = datetime.utcnow()
        logger.debug(f"Call start time set to {call_start_time}")

        if bot_pipeline.audio_buffer_processor:
            logger.debug("Starting audio buffer recording")
            await bot_pipeline.audio_buffer_processor.start_recording()
            logger.debug("Audio recording started")

        # Get node config from Bot instance
        logger.info(f"Retrieving node configuration from bot {bot_identifier}")
        node_config = await bot.get_initial_node(bot_pipeline.flow_manager.state)
        logger.debug(f"Node configuration retrieved: {node_config}")

        # Inject language instruction if multilingual support is enabled
        if language_info:
            language_instruction = {
                "role": "system",
                "content": f"""CRITICAL LANGUAGE INSTRUCTION: You MUST respond ONLY in {language_info['name']} ({language_info['native']}). 
This is a strict requirement - every single response you give must be in {language_info['name']}. 
Do not use English or any other language under any circumstances. 
The user will speak to you in {language_info['name']}, and you must respond exclusively in {language_info['name']}.
Maintain natural, fluent {language_info['name']} throughout the entire conversation.""",
            }
            # Prepend the language instruction to role_messages
            # Handle both dict and NodeConfig object
            if hasattr(node_config, "role_messages"):
                node_config.role_messages.insert(0, language_instruction)
                # DO NOT enable respond_immediately - we have a pre-configured greeting
                # The greeting will be played via initial_audio_phrase
            else:
                node_config["role_messages"].insert(0, language_instruction)
                # DO NOT enable respond_immediately - we have a pre-configured greeting
                # The greeting will be played via initial_audio_phrase
            logger.info(
                f"Injected {language_info['name']} language instruction into system prompt (respond_immediately disabled - using pre-configured greeting)"
            )

        logger.info("Initializing flow manager with node configuration")
        await bot_pipeline.flow_manager.initialize(node_config)
        logger.debug("Flow manager initialized successfully")

        logger.debug(f"Marking chat conversation {chat_conversation.id} as active")
        await chat_conversation.mark_active()
        logger.debug("Chat conversation marked as active")

    @bot_pipeline.audio_buffer_processor.event_handler("on_audio_data")
    async def on_audio_data(_buffer, audio, sample_rate, num_channels):
        nonlocal audio_path
        logger.debug(f"Received audio data of length {len(audio)} bytes")
        if len(audio) > 0:
            filename = f"/tmp/recording_{stream_config.bot_session_id}.mp3"

            # Create WAV data in memory first
            with io.BytesIO() as wav_buffer:
                with wave.open(wav_buffer, "wb") as wf:
                    wf.setsampwidth(2)
                    wf.setnchannels(num_channels)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                wav_buffer.seek(0)

                # Convert WAV to MP3 using pydub
                audio_segment = AudioSegment.from_wav(wav_buffer)

                # Export as MP3
                with io.BytesIO() as mp3_buffer:
                    audio_segment.export(mp3_buffer, format="mp3")
                    async with aiofiles.open(filename, "wb") as file:
                        await file.write(mp3_buffer.getvalue())

            logger.info(f"Merged audio saved to {filename}")

            audio_path = await bot_pipeline.file_store.save_recording(
                session_id=stream_config.bot_session_id, local_path=filename
            )

            logger.info(f"Audio saved to file store at {audio_path}")

            logger.info(f"Deleting temporary audio file {filename}")
            try:
                os.remove(filename)
            except Exception as e:
                logger.error(f"Error deleting temporary audio file {filename}: {e}")

        else:
            logger.info("No audio data to save")

    @bot_pipeline.transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.debug("client disconnect triggered")
        nonlocal chat_closed_reason, call_end_time
        call_end_time = datetime.utcnow()
        chat_closed_reason = ChatCloseReason.USER_DISCONNECTED
        await bot_pipeline.task.cancel()
        logger.debug("Client USER disconnect triggered")

    def phrase_matches(utterance, match_target):
        utterance = utterance.replace("।", " ").lower()
        utterance_tokens = nltk.word_tokenize(utterance)
        target_tokens = nltk.word_tokenize(match_target.lower())
        matches = 0
        for i in target_tokens:
            if i in utterance_tokens:
                matches += 1
        match_ratio = matches / len(target_tokens)
        logger.debug(f"Match ratio for '{utterance} <-> {match_target}': {match_ratio}")
        if match_ratio >= bot_config.pipeline_config.end_phrase_match_threshold:
            return True

    @bot_pipeline.transcript.event_handler("on_transcript_update")
    async def handle_transcript(_processor, frame):
        end_phrases = bot_config.pipeline_config.end_phrases or []

        logger.debug(f"Transcript update frame: {frame}")
        # bot_messages = []
        if isinstance(frame, TranscriptionUpdateFrame):
            for transcript in frame.messages:
                # for end frame
                logger.debug(
                    f"Transcript update: {transcript.role}: {transcript.content}"
                )
                content = transcript.content
                if content and (
                    transcript.role == "user" or transcript.role == "assistant"
                ):
                    # Store message in db
                    chat_message = ChatMessageNew(
                        content=transcript.content,
                        role=transcript.role,
                        conversation_id=chat_conversation.id,
                        bot_identifier=bot_identifier,
                    )
                    await chat_message.insert()

                    call_transcript_data.append(
                        {
                            "role": transcript.role,
                            "content": transcript.content,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                if not content or transcript.role != "assistant":
                    continue
                logger.debug(
                    f"Transcript update 1: {transcript.role}: {transcript.content}"
                )
                for phrase in end_phrases:
                    if phrase_matches(content, phrase):
                        logger.debug(
                            f"Ending call due to end phrase: {phrase} matched bot utterance: {content}"
                        )
                        nonlocal chat_closed_reason
                        chat_closed_reason = ChatCloseReason.CALL_END_PHRASE_TRIGGERED
                        await bot_pipeline.task.queue_frame(EndFrame())
                        return

    # Play initial audio phrase immediately after pipeline creation and event handlers registration
    # This ensures it's the very first thing processed and transcript events are captured
    await bot_pipeline.play_initial_audio()

    # Associate the flow manager with the bot
    logger.info(f"Setting flow manager for bot {bot_identifier}")
    # await bot.set_flow_manager(bot_pipeline.flow_manager)
    logger.debug("Flow manager successfully associated with the bot")

    logger.info(f"Starting bot pipeline execution for bot {bot_identifier}")
    await bot_pipeline.run()
    logger.info("Bot pipeline execution completed")

    # Save transcript and get call details
    logger.info(f"Saving transcript for session {stream_config.bot_session_id}")
    formatted_transcript = "\n".join(
        [
            f"{m['role']}: {m.get('content', 'N/A')}"
            for m in call_transcript_data
            if m["role"] in ["user", "assistant"]
        ]
    )
    logger.debug(
        f"Formatted transcript: {formatted_transcript[:100]}..."
        if len(formatted_transcript) > 100
        else formatted_transcript
    )

    transcript_path = await bot_pipeline.file_store.save_transcript(
        session_id=stream_config.bot_session_id,
        transcript=formatted_transcript,
    )
    logger.info(f"Transcript saved to file store at {transcript_path}")
    logger.debug("Bot pipeline finished running")

    # Close conversation
    logger.info(
        f"Closing conversation {chat_conversation.id} with reason: {chat_closed_reason}"
    )
    chat_conversation = await chat_conversation.close_conversation(
        close_reason=chat_closed_reason,
        transcript_path=transcript_path,
        recording_audio_path=audio_path,
        call_end_time=call_end_time,
    )
    logger.info(
        f"Closed chat conversation with ID: {chat_conversation.id} for user: {chat_conversation.user_id} with reason: {chat_closed_reason}"
    )
    logger.debug(
        f"Conversation close details - transcript: {transcript_path}, recording: {audio_path}, end time: {call_end_time}"
    )
    await bot.run_postcall_analysis(
        chat_conversation, call_transcript_data, stream_config
    )
