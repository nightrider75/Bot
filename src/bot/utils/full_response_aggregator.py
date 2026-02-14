#
# Smart Text Aggregator for Streaming TTS
#
# This aggregator buffers text and releases it in larger chunks (multiple sentences)
# to reduce gaps between TTS calls while maintaining low latency.
#
# It releases text when it accumulates enough content (minimum characters)
# AND hits a sentence boundary, providing a balance between latency and smoothness.
#

from typing import Optional

from bot_engine.utils.text.base_text_aggregator import BaseTextAggregator
from bot_engine.utils.string import match_endofsentence


class FullResponseTextAggregator(BaseTextAggregator):
    """Text aggregator that buffers multiple sentences before releasing.

    Unlike SimpleTextAggregator which releases at every sentence boundary,
    this aggregator buffers text until it has accumulated a minimum amount
    of content AND hits a sentence boundary. This reduces the number of
    TTS calls and gaps between audio chunks while maintaining reasonable latency.
    
    The aggregator releases text when:
    1. Text length >= min_chars AND a sentence boundary is found
    2. This creates fewer, longer TTS calls = smoother audio
    """

    def __init__(self, min_chars: int = 150):
        """Initialize the smart text aggregator.
        
        Args:
            min_chars: Minimum characters to buffer before releasing at sentence boundary.
                       Default 150 chars (~2-3 sentences) provides good balance.
        """
        self._text = ""
        self._min_chars = min_chars

    @property
    def text(self) -> str:
        """Get the currently aggregated text.

        Returns:
            The text that has been accumulated.
        """
        return self._text

    async def aggregate(self, text: str) -> Optional[str]:
        """Aggregate text and release when enough content is buffered.

        Accumulates text tokens and releases them when:
        - At least min_chars have accumulated AND
        - A sentence boundary is detected
        
        This creates larger chunks for TTS, reducing gaps between audio.

        Args:
            text: New text to add to the aggregation buffer.

        Returns:
            Buffered text if release conditions are met, None otherwise.
        """
        self._text += text
        
        # Only consider releasing if we have enough content
        if len(self._text) >= self._min_chars:
            # Look for sentence boundary
            eos_end_marker = match_endofsentence(self._text)
            if eos_end_marker:
                result = self._text[:eos_end_marker]
                self._text = self._text[eos_end_marker:]
                return result
        
        return None

    async def handle_interruption(self):
        """Handle interruptions by clearing the text buffer."""
        self._text = ""

    async def reset(self):
        """Clear the internally aggregated text."""
        self._text = ""
