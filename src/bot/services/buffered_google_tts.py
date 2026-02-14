#
# Buffered Google TTS Service
#
# This is a wrapper around GoogleTTSService that pre-buffers audio
# before sending it to the client, eliminating jitter and choppiness.
#

import asyncio
from typing import AsyncGenerator, Optional

from loguru import logger
from pydantic import BaseModel

from bot_engine.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from bot_engine.services.tts_service import TTSService
from bot_engine.transcriptions.language import Language
from bot_engine.utils.tracing.service_decorators import traced_tts

from google.cloud import texttospeech_v1
from google.auth import default
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account


def language_to_google_tts_language(language: Language) -> Optional[str]:
    """Convert a Language enum to Google TTS language code."""
    BASE_LANGUAGES = {
        Language.AR: "ar-XA",
        Language.BG: "bg-BG",
        Language.CA: "ca-ES",
        Language.CS: "cs-CZ",
        Language.DA: "da-DK",
        Language.DE: "de-DE",
        Language.EL: "el-GR",
        Language.EN: "en-US",
        Language.ES: "es-ES",
        Language.EU: "eu-ES",
        Language.FI: "fi-FI",
        Language.FIL: "fil-PH",
        Language.FR: "fr-FR",
        Language.GL: "gl-ES",
        Language.HE: "he-IL",
        Language.HI: "hi-IN",
        Language.HU: "hu-HU",
        Language.ID: "id-ID",
        Language.IT: "it-IT",
        Language.JA: "ja-JP",
        Language.KO: "ko-KR",
        Language.LT: "lt-LT",
        Language.LV: "lv-LV",
        Language.MS: "ms-MY",
        Language.NL: "nl-NL",
        Language.NO: "nb-NO",
        Language.PL: "pl-PL",
        Language.PT: "pt-PT",
        Language.RO: "ro-RO",
        Language.RU: "ru-RU",
        Language.SK: "sk-SK",
        Language.SV: "sv-SE",
        Language.TH: "th-TH",
        Language.TR: "tr-TR",
        Language.UK: "uk-UA",
        Language.VI: "vi-VN",
        Language.ZH: "cmn-CN",
    }

    result = BASE_LANGUAGES.get(language)
    if result:
        return result

    lang_str = str(language.value)
    if "-" in lang_str:
        return lang_str

    base_code = lang_str.split("-")[0].upper()
    for lang, code in BASE_LANGUAGES.items():
        if code.startswith(base_code.lower()) or code.startswith(f"{base_code}-"):
            return code

    return None


class BufferedGoogleTTSService(TTSService):
    """Google TTS service with pre-buffering for smooth audio playback.
    
    This service collects ALL audio from Google's streaming API first,
    then sends it in smooth, evenly-timed chunks to eliminate jitter.
    """

    class InputParams(BaseModel):
        """Input parameters for Google streaming TTS configuration."""
        language: Optional[Language] = Language.EN
        speaking_rate: Optional[float] = None

    def __init__(
        self,
        *,
        credentials: Optional[str] = None,
        credentials_path: Optional[str] = None,
        voice_id: str = "en-US-Chirp3-HD-Charon",
        sample_rate: Optional[int] = None,
        params: InputParams = None,
        # Pre-buffer this many seconds of audio before starting playback
        pre_buffer_seconds: float = 0.3,
        **kwargs,
    ):
        """Initialize the buffered Google TTS service.
        
        Args:
            pre_buffer_seconds: How many seconds of audio to buffer before
                               starting playback. Higher = smoother but more latency.
        """
        super().__init__(sample_rate=sample_rate, **kwargs)

        params = params or BufferedGoogleTTSService.InputParams()

        self._settings = {
            "language": (
                language_to_google_tts_language(params.language) if params.language else "en-US"
            ),
            "speaking_rate": params.speaking_rate,
        }
        self.set_voice(voice_id)
        self._pre_buffer_seconds = pre_buffer_seconds
        self._client = self._create_client(credentials, credentials_path)

    def _create_client(self, credentials: Optional[str], credentials_path: Optional[str]):
        import json
        creds = None

        if credentials:
            json_account_info = json.loads(credentials)
            creds = service_account.Credentials.from_service_account_info(json_account_info)
        elif credentials_path:
            creds = service_account.Credentials.from_service_account_file(credentials_path)
        else:
            try:
                creds, project_id = default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            except GoogleAuthError:
                pass

        if not creds:
            raise ValueError("No valid credentials provided.")

        return texttospeech_v1.TextToSpeechAsyncClient(credentials=creds)

    def can_generate_metrics(self) -> bool:
        return True

    def language_to_service_language(self, language: Language) -> Optional[str]:
        return language_to_google_tts_language(language)

    @traced_tts
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate speech with pre-buffering for smooth playback."""
        logger.debug(f"{self}: Generating TTS with pre-buffering [{text}]")

        try:
            await self.start_ttfb_metrics()

            voice = texttospeech_v1.VoiceSelectionParams(
                language_code=self._settings["language"], 
                name=self._voice_id
            )

            streaming_config = texttospeech_v1.StreamingSynthesizeConfig(
                voice=voice,
                streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
                    audio_encoding=texttospeech_v1.AudioEncoding.PCM,
                    sample_rate_hertz=self.sample_rate,
                    speaking_rate=self._settings["speaking_rate"],
                ),
            )
            config_request = texttospeech_v1.StreamingSynthesizeRequest(
                streaming_config=streaming_config
            )

            async def request_generator():
                yield config_request
                yield texttospeech_v1.StreamingSynthesizeRequest(
                    input=texttospeech_v1.StreamingSynthesisInput(text=text)
                )

            streaming_responses = await self._client.streaming_synthesize(request_generator())
            await self.start_tts_usage_metrics(text)

            # Collect ALL audio first
            all_audio = bytearray()
            async for response in streaming_responses:
                chunk = response.audio_content
                if chunk:
                    all_audio.extend(chunk)

            await self.stop_ttfb_metrics()

            if not all_audio:
                logger.warning(f"{self}: No audio generated for text: {text}")
                return

            yield TTSStartedFrame()

            # Now send in smooth, evenly-sized chunks
            CHUNK_SIZE = self.chunk_size  # 0.5 seconds worth of audio
            audio_bytes = bytes(all_audio)
            
            for i in range(0, len(audio_bytes), CHUNK_SIZE):
                chunk = audio_bytes[i:i + CHUNK_SIZE]
                yield TTSAudioRawFrame(chunk, self.sample_rate, 1)

            yield TTSStoppedFrame()

        except Exception as e:
            logger.exception(f"{self} error generating TTS: {e}")
            yield ErrorFrame(error=f"TTS generation error: {str(e)}")
