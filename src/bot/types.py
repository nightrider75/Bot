"""Core type definitions for the bot orchestration system.

This module defines the fundamental data types and configuration models used throughout
the bot system. It includes enumerations for different service providers
(transport, STT, LLM, TTS) and configuration classes for each component of the
voice bot pipeline.

The configuration hierarchy is:
- BotConfig: Top-level configuration combining all components
  - PipelineConfig: Overall conversation flow settings
  - TransportConfig: Audio streaming and VAD settings
  - TranscriberConfig: Speech-to-text settings
  - AgentConfig: Language model settings
  - SynthesizerConfig: Text-to-speech settings
  - FileStoreConfig: File storage settings

All configuration classes use Pydantic for validation and serialization.
"""

from enum import StrEnum
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel
from bot_engine.processors.filters.stt_mute_filter import (
    STTMuteStrategy as InternalSTTMuteStrategy,
)

from bot.store.file_store import types as file_store_types

FileStoreConfig = file_store_types.FileStoreConfig
FileStoreTypes = file_store_types.FileStoreTypes


class AssetType(StrEnum):
    """Type of platform asset."""

    INITIAL_AUDIO = "initial_audio"


class TransportType(StrEnum):
    """Enumeration of supported transport providers for audio streaming.

    Defines the available transport mechanisms for handling audio streams,
    including telephony providers and websocket connections.
    """

    TWILIO = "twilio"
    OZONOTEL = "ozonotel"
    PLIVO = "plivo"
    WEBRTC = "webrtc"
    TELNYX = "telnyx"
    EXOTEL = "exotel"
    BOT_WEBSOCKET = "bot_websocket"
    ASTERISK = "asterisk"


class TranscriberType(StrEnum):
    """Enumeration of supported speech-to-text (STT) transcription providers.

    Defines the available speech recognition services that can be used
    for converting audio to text.
    """

    DEEPGRAM = "deepgram"
    AZURESTT = "azurestt"
    AZUREOPENAI = "azureopenai"
    BOTSTT = "botstt"
    GOOGLESTT = "googlestt"
    ELEVENLABS = "elevenlabs"


class LLMType(StrEnum):
    """Enumeration of supported Large Language Model providers.

    Defines the available LLM services that can be used for natural
    language processing and conversation generation.
    """

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    AZUREOPENAI = "azureopenai"
    CEREBRAS = "cerebras"
    FIREWORKS = "fireworks"
    GROQ = "groq"


class SynthesizerType(StrEnum):
    """Enumeration of supported text-to-speech (TTS) synthesis providers.

    Defines the available speech synthesis services that can be used
    for converting text to natural-sounding speech.
    """

    ELEVENLABS = "elevenlabs"
    AZURETTS = "azuretts"
    GOOGLETTS = "googletts"
    CARTESIA = "cartesia"
    OPENAI = "openai"


class VadParams(BaseModel):
    """Configuration parameters for Voice Activity Detection (VAD).

    Contains settings that control the sensitivity and behavior of the
    voice activity detection system.

    Attributes:
        enabled: Whether VAD is active
        start_secs: Duration of voice required to start capture
        stop_secs: Duration of silence required to end capture
        confidence_threshold: Required confidence for voice detection
        volume_threshold: Minimum volume level for detection
    """

    enabled: bool = True
    start_secs: float = 0.4
    stop_secs: float = 0.8
    confidence_threshold: float = 0.85
    volume_threshold: float = 0.65


class StreamConfig(BaseModel):
    """Configuration for an audio stream session.

    Contains identifiers and settings for managing an individual audio
    stream connection with a user.

    Attributes:
        stream_id: Unique identifier for the stream
        call_id: Associated call identifier
        account_id: Account identifier for the user
        outbound_encoding: Audio encoding format, defaults to PCMU for telephony
        user_id: Identifier of the connected user
        bot_session_id: UUID for the bot session
        host_id: Identifier of the host system
        bot_assistant_id: Optional platform assistant identifier tied to this call
    """

    stream_id: str | None = None
    call_id: str | None = None
    account_id: str | None = None
    outbound_encoding: str | None = "PCMU"  # Default to PCMU for telephony
    user_id: str | None = None
    bot_session_id: UUID
    host_id: str
    bot_assistant_id: str | None = None


class TransportConfig(BaseModel):
    """Configuration for the transport layer handling audio streams.

    Defines settings for managing audio transport, including provider selection,
    voice activity detection, and session management.

    Attributes:
        provider: The transport provider to use
        vad_params: Voice Activity Detection parameters
        session_timeout: Timeout duration in seconds for inactive sessions
    """

    provider: TransportType | None = None
    vad_params: VadParams = VadParams()
    session_timeout: int | None = 3  # in seconds


class TranscriberConfig(BaseModel):
    """Configuration for the speech-to-text transcription service.

    Contains settings for the STT service, including provider selection,
    model configuration, and language settings.

    Attributes:
        provider: The STT provider to use
        model: Name of the transcription model to use
        api_key: Authentication key for the provider
        language: List of supported languages
        region: Geographic region for the service
        endpoint: Custom endpoint URL if required
        phrase_list: List of phrases to optimize recognition for
    """

    provider: TranscriberType = TranscriberType.DEEPGRAM
    model: str | None = None
    api_key: str | None = None
    credentials_path: str | None = None
    language: list[str] | None = None
    region: str | None = None
    endpoint: str | None = None
    phrase_list: list[str] | None = None


class AgentConfig(BaseModel):
    """Configuration for the LLM-based conversational agent.

    Contains settings for the language model service that powers
    the conversational capabilities of the bot.

    Attributes:
        provider: The LLM provider to use
        model: Name of the language model to use
        temperature: Sampling temperature for response generation
        api_key: Authentication key for the provider
        endpoint: Custom endpoint URL if required
    """

    provider: LLMType = LLMType.OPENAI
    model: str | None = None
    temperature: float | None = None
    api_key: str | None = None
    endpoint: str | None = None


class SynthesizerConfig(BaseModel):
    """Configuration for the text-to-speech synthesis service.

    Contains settings for the TTS service, including voice selection,
    pronunciation rules, and text normalization options.

    Attributes:
        provider: The TTS provider to use
        model: Name of the synthesis model to use
        voice_id: Identifier for the specific voice to use
        api_key: Authentication key for the provider
        region: Geographic region for the service (e.g., Azure region)
        pronounciation_mapping: Dictionary of text to pronunciation mappings
        pronounciation_mapping_case_sensitive: Whether mappings are case-sensitive
        enable_number_normalization: Whether to convert numbers to words
        number_normalization_language: Language for number conversion
    """

    provider: SynthesizerType = SynthesizerType.ELEVENLABS
    model: str | None = None
    voice_id: str | None = None
    api_key: str | None = None
    region: str | None = None
    credentials_path: str | None = None
    pronounciation_mapping: dict[str, str] = {}
    pronounciation_mapping_case_sensitive: bool = True
    enable_number_normalization: bool = False
    number_normalization_language: str | None = "en"
    language: str = "en"
    endpoint: str | None = None
    speed: str | None = None
    expressive_level: int | None = None


class PostCallConfig(BaseModel):
    """Configuration for post-call actions and processing.

    Contains settings for handling actions to be taken after a call
    has ended, such as saving call recordings or transcriptions.

    Attributes:
        save_recording: Whether to save the call recording
        save_transcription: Whether to save the call transcription
        recording_format: Format to save the recording in (e.g., mp3, wav)
        transcription_format: Format to save the transcription in (e.g., txt, json)
        storage_path: Path or bucket where files should be stored
    """

    gcs_pubsub_topics: Union[List[str], str] = list()
    gcs_pubsub_project_id: str | None = None
    credentials: Optional[str] = None
    credentials_path: Optional[str] = None


class BotSTTMuteStrategy(StrEnum):
    """Strategies determining when STT should be muted.

    Each strategy defines different conditions under which speech-to-text
    processing should be temporarily disabled to prevent unwanted audio
    processing during specific conversation states.

    Parameters:
        FIRST_SPEECH: Mute STT until the first bot speech is detected.
        MUTE_UNTIL_FIRST_BOT_COMPLETE: Mute STT until the first bot completes speaking,
        regardless of whether it is the first speech.
        FUNCTION_CALL: Mute STT during function calls to prevent interruptions.
        ALWAYS: Always mute STT when the bot is speaking.
    """

    FIRST_SPEECH = "first_speech"
    MUTE_UNTIL_FIRST_BOT_COMPLETE = "mute_until_first_bot_complete"
    FUNCTION_CALL = "function_call"
    ALWAYS = "always"

    def to_internal(self) -> InternalSTTMuteStrategy:
        if self is BotSTTMuteStrategy.FIRST_SPEECH:
            return InternalSTTMuteStrategy.FIRST_SPEECH
        elif self is BotSTTMuteStrategy.MUTE_UNTIL_FIRST_BOT_COMPLETE:
            return InternalSTTMuteStrategy.MUTE_UNTIL_FIRST_BOT_COMPLETE
        elif self is BotSTTMuteStrategy.FUNCTION_CALL:
            return InternalSTTMuteStrategy.FUNCTION_CALL
        elif self is BotSTTMuteStrategy.ALWAYS:
            return InternalSTTMuteStrategy.ALWAYS


class PipelineConfig(BaseModel):
    """Configuration for the overall conversation pipeline.

    Contains settings that control the behavior of the conversation flow,
    including idle detection, conversation termination, and timeouts.

    Attributes:
        audio_recording: Whether to record the conversation audio
        initial_audio_id: UUID of the initial audio asset (fetched from asset store)
        initial_audio_rate: Sample rate of the initial audio
        initial_audio_phrase: Phrase to use as initial audio
        llm_aggregation_timeout: Time to wait for LLM responses in seconds
        user_idle_enabled: Whether to enable idle user detection
        user_idle_timeout: Time in seconds before considering user idle
        user_idle_retries: Number of attempts to re-engage idle user
        user_idle_nudge: Message to send when checking for user presence
        user_idle_goodbye: Message to send when ending due to inactivity
        user_idle_llm_nudge: System prompt to inject before running the LLM when nudging
        user_idle_llm_goodbye: System prompt to inject before running the LLM when ending due to inactivity
        end_phrases: List of phrases that trigger conversation end
        end_phrase_match_threshold: Required similarity for end phrase matching
        max_ttl_enabled: Whether to enable maximum conversation duration
        max_ttl_timeout: Maximum conversation duration in seconds
    """

    audio_recording: bool = True

    # Initial audio configuration
    initial_audio_id: UUID | None = None  # UUID string of the asset
    initial_audio_rate: int | None = None
    initial_audio_phrase: str | None = None
    # User Idle params
    llm_aggregation_timeout: float = 0.3  # in seconds
    user_idle_enabled: bool = False
    user_idle_timeout: int = 10  # in seconds
    user_idle_retries: int = 3
    user_idle_nudge: str = "Are you still there?"
    user_idle_goodbye: str = "Good bye!"
    user_idle_llm_nudge: str | None = None
    user_idle_llm_goodbye: str | None = None
    # End phrases configuration
    end_phrases: list[str] | None = None
    end_phrase_match_threshold: float = 0.8
    # Max TTL configuration
    max_ttl_enabled: bool = False
    max_ttl_timeout: float = 600.0  # in seconds (10 minutes default)
    postcall_config: PostCallConfig | None = PostCallConfig()
    stt_mute_strategy: List[BotSTTMuteStrategy] = list()


class BotConfig(BaseModel):
    """Main configuration class for a voice bot instance.

    Combines all the component configurations needed to run a complete
    voice bot, including speech-to-text, language model, text-to-speech,
    and transport settings.

    Attributes:
        bot_identifier: Unique identifier for the bot instance
        pipeline_config: Settings for the conversation pipeline
        tts: Text-to-speech synthesis configuration
        stt: Speech-to-text transcription configuration
        llm: Language model configuration
        transport: Audio transport configuration
    """

    bot_identifier: UUID
    pipeline_config: PipelineConfig = PipelineConfig()
    tts: SynthesizerConfig = SynthesizerConfig()
    stt: TranscriberConfig = TranscriberConfig()
    llm: AgentConfig = AgentConfig()
    transport: TransportConfig = TransportConfig()
    file_store: FileStoreConfig = FileStoreConfig()
