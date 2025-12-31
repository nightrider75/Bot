from datetime import datetime, timezone
from typing import Any, Dict, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from indic_numtowords import num2words as _indic_num2words
from jinja2 import Template
from loguru import logger
from num2words import num2words as _generic_num2words

_INDIC_LANGUAGES = {
    "en",
    "hi",
    "ne",
    "gu",
    "mr",
    "bn",
    "te",
    "ta",
    "kn",
    "or",
    "pa",
    "ml",
}

_FORMAT_MAP = {"cardinal", "currency", "ordinal"}

NumberInput = Union[str, int, float]


def _sanitize_numeric_string(value: str) -> str:
    sanitized = value.strip()
    for char in (",", " ", "%"):
        sanitized = sanitized.replace(char, "")
    return sanitized


def num_to_words(
    number: NumberInput, language: str = "en", format: str = "cardinal"
) -> str:
    language_value = (language or "en").strip()
    if not language_value:
        language_value = "en"
    language_value = language_value.lower()

    format_key = str(format or "cardinal").strip().lower()
    if format_key not in _FORMAT_MAP:
        logger.error(f"Unsupported format: {format}")
        return ""

    if isinstance(number, str):
        sanitized = _sanitize_numeric_string(number)
        if not sanitized:
            logger.error(f"Unable to sanitize numeric string: '{number}'")
            return ""

        try:
            normalized_number = float(sanitized)
        except ValueError:
            logger.error(f"Unable to convert '{number}' to a number")
            return ""
    elif isinstance(number, (int, float)):
        normalized_number = number
    else:
        logger.error("number must be an int, float, or numeric string")
        return ""

    language_code = language_value.split("-", 1)[0]
    use_indic = language_code in _INDIC_LANGUAGES
    library_language = language_code if use_indic else language_value

    if use_indic:
        try:
            return _indic_num2words(normalized_number, lang=library_language)
        except Exception as exc:  # pragma: no cover
            logger.error(f"Indic conversion failed: {exc}")
            return ""

    try:
        return _generic_num2words(
            normalized_number, lang=library_language, to=format_key
        )
    except Exception as exc:  # pragma: no cover
        logger.error(f"Generic conversion failed: {exc}")
        return ""


def _resolve_timezone(timezone_hint: Union[str, None]) -> timezone:
    candidate = (timezone_hint or "").strip()
    if not candidate:
        candidate = "UTC"

    try:
        return ZoneInfo(candidate)
    except ZoneInfoNotFoundError as exc:
        logger.error(f"Invalid timezone '{timezone_hint}': {exc}")

    return timezone.utc


def current_time(
    timezone_name: Union[str, None] = "UTC", output_format: Union[str, None] = None
) -> str:
    tz = _resolve_timezone(timezone_name)
    now = datetime.now(tz)
    fmt = (output_format or "").strip()
    if fmt:
        try:
            return now.strftime(fmt)
        except (TypeError, ValueError) as exc:
            logger.error(f"Invalid current_time format '{output_format}': {exc}")
    return now.timetz().isoformat()


def templatize(text: str, data: Dict[str, Any]) -> str:
    data["current_date"] = datetime.now().strftime("%Y-%B-%d")
    data["current_weekday"] = datetime.now().strftime("%A")
    logger.info(f"Templatizing prompt: {text} with data: {data}")
    template = Template(text)
    template.globals["to_words"] = num_to_words
    template.globals["current_time"] = current_time
    return template.render(data)
