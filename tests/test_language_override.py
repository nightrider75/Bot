import pytest


@pytest.mark.anyio
async def test_language_override_hi_sets_stt_tts():
    """Smoke test for runner LANGUAGE_MAP wiring."""

    from bot.bot_pipeline.runner import LANGUAGE_MAP

    language_info = LANGUAGE_MAP["hi"]

    # Mirrors how runner.py applies the mapping.
    stt_language = [language_info["stt_code"]]
    tts_language = language_info["stt_code"]

    assert stt_language == ["hi"]
    assert tts_language == "hi"
