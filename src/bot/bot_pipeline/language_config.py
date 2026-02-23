"""
Language configuration for multi-language TTS and STT support.
Maps language codes to appropriate voice IDs and settings for different TTS providers.
"""

from typing import Dict, Tuple


class LanguageConfig:
    """
    Configuration for multi-language support with Google Cloud TTS and Deepgram STT.
    
    IMPORTANT: Google TTS streaming synthesis ONLY supports Chirp voices!
    Neural2 voices will fail with: "Currently, only Chirp 3: HD voices are supported for streaming synthesis."
    """

    # Google TTS Voice Mappings - MUST USE CHIRP3-HD VOICES FOR STREAMING
    # Format: language_code -> (voice_id, language_code_for_tts)
    # Using Chirp3-HD-Aoede (female voice) for all languages - ALL support streaming!
    # NOTE: Keys must be LOWERCASE because get_google_voice_for_language() lowercases the input!
    GOOGLE_TTS_VOICES: Dict[str, Tuple[str, str]] = {
        # English variants - Chirp3-HD voices (streaming-compatible)
        "en": ("en-US-Chirp3-HD-Aoede", "en-US"),  # Default English (US)
        "en-us": ("en-US-Chirp3-HD-Aoede", "en-US"),  # US English
        "en-gb": ("en-GB-Chirp3-HD-Aoede", "en-GB"),  # UK English
        "en-in": ("en-IN-Chirp-HD-O", "en-IN"),  # Indian English
        "en-au": ("en-AU-Chirp3-HD-Aoede", "en-AU"),  # Australian English
        # Hindi - Now has Chirp3-HD support!
        "hi": ("hi-IN-Chirp3-HD-Aoede", "hi-IN"),  # Hindi (female)
        "hi-in": ("hi-IN-Chirp3-HD-Aoede", "hi-IN"),
        # German - Now has Chirp3-HD support!
        "de": ("de-DE-Chirp3-HD-Aoede", "de-DE"),  # German (female)
        "de-de": ("de-DE-Chirp3-HD-Aoede", "de-DE"),
        # French - Now has Chirp3-HD support!
        "fr": ("fr-FR-Chirp3-HD-Aoede", "fr-FR"),  # French (female)
        "fr-fr": ("fr-FR-Chirp3-HD-Aoede", "fr-FR"),
        # Spanish - Now has Chirp3-HD support!
        "es": ("es-ES-Chirp3-HD-Aoede", "es-ES"),  # Spanish Spain (female)
        "es-es": ("es-ES-Chirp3-HD-Aoede", "es-ES"),
        "es-us": ("es-US-Chirp3-HD-Aoede", "es-US"),  # Spanish US
        # Arabic - Now has Chirp3-HD support!
        "ar": ("ar-XA-Chirp3-HD-Aoede", "ar-XA"),  # Arabic (female)
        "ar-xa": ("ar-XA-Chirp3-HD-Aoede", "ar-XA"),
    }

    # STT Language Mappings (Deepgram)
    # Format: language_code -> deepgram_language_code
    DEEPGRAM_STT_LANGUAGES: Dict[str, str] = {
        "en": "en-US",
        "en-US": "en-US",
        "en-GB": "en-GB",
        "en-IN": "en-IN",
        "en-AU": "en-AU",
        "hi": "hi",
        "hi-IN": "hi",
        "de": "de",
        "de-DE": "de",
        "fr": "fr",
        "fr-FR": "fr",
        "es": "es",
        "es-ES": "es",
        "es-US": "es",
        "ar": "ar",
        "ar-XA": "ar",
    }

    # Friendly language names for logging
    LANGUAGE_NAMES: Dict[str, str] = {
        "en": "English (US)",
        "en-US": "English (US)",
        "en-GB": "English (UK)",
        "en-IN": "English (India)",
        "en-AU": "English (Australia)",
        "hi": "Hindi",
        "hi-IN": "Hindi",
        "de": "German",
        "de-DE": "German",
        "fr": "French",
        "fr-FR": "French",
        "es": "Spanish",
        "es-ES": "Spanish (Spain)",
        "es-US": "Spanish (US)",
        "ar": "Arabic",
        "ar-XA": "Arabic",
    }

    @classmethod
    def get_google_voice_for_language(cls, language_code: str) -> Tuple[str, str]:
        """
        Get Google TTS voice ID and language code for a given language.

        Args:
            language_code: Language code (e.g., 'en-US', 'hi', 'de')

        Returns:
            Tuple of (voice_id, tts_language_code)
            Defaults to English (US) if language not found.
        """
        # Normalize language code
        language_code = language_code or "en"
        language_code = language_code.strip().lower()

        # Try exact match first
        if language_code in cls.GOOGLE_TTS_VOICES:
            return cls.GOOGLE_TTS_VOICES[language_code]

        # Try base language (e.g., 'hi' from 'hi-IN')
        base_lang = language_code.split("-")[0]
        if base_lang in cls.GOOGLE_TTS_VOICES:
            return cls.GOOGLE_TTS_VOICES[base_lang]

        # Default to English (US)
        return cls.GOOGLE_TTS_VOICES["en"]

    @classmethod
    def get_deepgram_language(cls, language_code: str) -> str:
        """
        Get Deepgram STT language code for a given language.

        Args:
            language_code: Language code (e.g., 'en-US', 'hi', 'de')

        Returns:
            Deepgram language code
            Defaults to 'en-US' if language not found.
        """
        language_code = language_code or "en"
        language_code = language_code.strip().lower()

        # Try exact match
        if language_code in cls.DEEPGRAM_STT_LANGUAGES:
            return cls.DEEPGRAM_STT_LANGUAGES[language_code]

        # Try base language
        base_lang = language_code.split("-")[0]
        if base_lang in cls.DEEPGRAM_STT_LANGUAGES:
            return cls.DEEPGRAM_STT_LANGUAGES[base_lang]

        # Default to English (US)
        return "en-US"

    @classmethod
    def get_language_name(cls, language_code: str) -> str:
        """Get friendly language name for logging."""
        language_code = language_code or "en"
        language_code = language_code.strip().lower()
        return cls.LANGUAGE_NAMES.get(language_code, language_code.upper())
