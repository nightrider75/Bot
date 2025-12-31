import aiohttp
from loguru import logger
from bot_engine.services.azure.stt import AzureSTTService
from bot_engine.transcriptions.language import Language
from bot_engine.services.deepgram.stt import DeepgramSTTService, LiveOptions
from bot_engine.services.google.stt import GoogleSTTService
from bot_engine.services.elevenlabs.stt import ElevenLabsSTTService

from bot.types import (
    PipelineConfig,
    TranscriberConfig,
    TranscriberType,
)


class TranscriberProvider:
    @classmethod
    def get_provider(cls, config: TranscriberConfig, pipeline_config: PipelineConfig):
        if config.provider == TranscriberType.DEEPGRAM:
            stt_language = None
            if config.language:
                if isinstance(config.language, str):
                    stt_language = config.language
                elif isinstance(config.language, list):
                    if len(config.language) == 1:
                        stt_language = config.language[0]
                    else:
                        stt_language = "multi"
            return DeepgramSTTService(
                api_key=config.api_key,
                live_options=LiveOptions(model=config.model, language=stt_language),
                audio_passthrough=pipeline_config.audio_recording,
            )
        elif config.provider == TranscriberType.AZURESTT:
            if not config.language:
                stt_language = Language.EN_US
            elif len(config.language) > 1:
                logger.error(
                    "Language detection not supported for AzureSTT, using the first language"
                )
                stt_language = Language(config.language[0])
            elif len(config.language) == 1:
                stt_language = Language(config.language[0])

            return AzureSTTService(
                api_key=config.api_key,
                base_url=config.endpoint,
                region=config.region,
                language=stt_language,
                phrase_list=config.phrase_list,
            )
        elif config.provider == TranscriberType.AZUREOPENAI:
            raise NotImplementedError("AzureOpenAI provider not implemented yet")
        elif config.provider == TranscriberType.BOTSTT:
            raise NotImplementedError("BotSTT provider not implemented yet")
        elif config.provider == TranscriberType.GOOGLESTT:
            stt_languages = []
            if config.language:
                if isinstance(config.language, str):
                    stt_languages = [Language(config.language)]
                elif isinstance(config.language, list):
                    stt_languages = [Language(lang) for lang in config.language]
            else:
                stt_languages = [Language.EN_US]

            google_params = GoogleSTTService.InputParams(
                languages=stt_languages,
                model=config.model or "latest_long",
                enable_automatic_punctuation=True,
                enable_interim_results=True,
            )

            return GoogleSTTService(
                credentials_path=config.credentials_path,
                location=config.region or "global",
                params=google_params,
            )
        elif config.provider == TranscriberType.ELEVENLABS:
            stt_language = None
            if config.language:
                if isinstance(config.language, str):
                    stt_language = Language(config.language)
                elif isinstance(config.language, list) and len(config.language) > 0:
                    if len(config.language) > 1:
                        logger.warning(
                            "Multiple languages not supported for ElevenLabsSTT, using the first language"
                        )
                    stt_language = Language(config.language[0])

            # Create aiohttp session for HTTP requests
            session = aiohttp.ClientSession()

            return ElevenLabsSTTService(
                api_key=config.api_key,
                aiohttp_session=session,
                model=config.model,
                params=ElevenLabsSTTService.InputParams(
                    language=stt_language,
                ),
            )
        else:
            raise ValueError(f"Unknown STT provider: {config.provider}")
