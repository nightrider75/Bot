from bot_engine.services.azure.tts import AzureTTSService
from bot_engine.services.cartesia.tts import CartesiaTTSService
from bot_engine.services.elevenlabs.tts import ElevenLabsTTSService
from bot_engine.services.google.tts import GoogleTTSService
from bot_engine.transcriptions.language import Language
from bot_engine.utils.text.map_text_filter import MapTextFilter
from bot_engine.utils.text.number_pronunciation_filter import (
    NumberPronunciationFilter,
)

from bot.types import SynthesizerConfig, SynthesizerType


class SynthesizerProvider:
    @classmethod
    def get_provider(cls, tts_config: SynthesizerConfig):
        text_filters = []

        # Add pronunciation mapping filter if configured
        if tts_config.pronounciation_mapping:
            text_filters.append(
                MapTextFilter(
                    params=MapTextFilter.InputParams(
                        mappings=tts_config.pronounciation_mapping,
                        enable_text_filter=True,
                        case_sensitive=tts_config.pronounciation_mapping_case_sensitive,
                    )
                )
            )

        # Add number normalization filter if enabled
        if tts_config.enable_number_normalization:
            text_filters.append(
                NumberPronunciationFilter(
                    params=NumberPronunciationFilter.InputParams(
                        enable_text_filter=True,
                        language=Language(
                            tts_config.number_normalization_language or "en"
                        ),
                    )
                )
            )

        if tts_config.provider == SynthesizerType.ELEVENLABS:
            try:
                elevenlabs_speed = float(tts_config.speed) if tts_config.speed else None
            except Exception:
                elevenlabs_speed = None
            return ElevenLabsTTSService(
                api_key=tts_config.api_key,
                voice_id=tts_config.voice_id,
                model=tts_config.model,
                text_filters=text_filters,
                params=ElevenLabsTTSService.InputParams(
                    stability=0.35,
                    similarity_boost=0.8,
                    style=0.8,
                    speed=elevenlabs_speed,
                    use_speaker_boost=True,
                ),
            )
        elif tts_config.provider == SynthesizerType.AZURETTS:
            return AzureTTSService(
                api_key=tts_config.api_key,
                region=tts_config.region,
                voice=tts_config.voice_id,
                text_filters=text_filters,
                params=AzureTTSService.InputParams(
                    language=Language(tts_config.language),
                ),
            )
        elif tts_config.provider == SynthesizerType.GOOGLETTS:
            return GoogleTTSService(
                credentials_path=tts_config.credentials_path,
                voice_id=tts_config.voice_id or "en-US-Chirp3-HD-Charon",
                text_filters=text_filters,
                params=GoogleTTSService.InputParams(
                    language=Language(tts_config.language),
                ),
            )
        elif tts_config.provider == SynthesizerType.CARTESIA:
            cartesia_speed = None
            if tts_config.speed in ["slow", "normal", "fast"]:
                cartesia_speed = tts_config.speed
            cartesia_params = CartesiaTTSService.InputParams(
                language=Language(tts_config.language), speed=cartesia_speed
            )
            return CartesiaTTSService(
                api_key=tts_config.api_key,
                voice_id=tts_config.voice_id,
                model=tts_config.model or "sonic-2",
                text_filters=text_filters,
                params=cartesia_params,
            )
        elif tts_config.provider == SynthesizerType.OPENAI:
            raise NotImplementedError("OpenAI provider not implemented yet")
