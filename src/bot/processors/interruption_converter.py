"""Interruption converter processor that converts UserStartedSpeakingFrame to InterruptionTaskFrame.

This processor sits in the pipeline and handles the conversion between user speaking
detection frames and interruption task frames to ensure TTS interruption works properly.
"""

from loguru import logger

from bot_engine.frames.frames import (
    Frame,
    InterruptionTaskFrame,
    UserStartedSpeakingFrame,
)
from bot_engine.processors.frame_processor import FrameDirection, FrameProcessor


class InterruptionConverterProcessor(FrameProcessor):
    """Processor that converts UserStartedSpeakingFrame to InterruptionTaskFrame.
    
    This processor is essential for WebSocket-based interruption systems where
    the frontend sends user_started_speaking messages that need to be converted
    to proper interruption frames to stop TTS processors.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames and convert UserStartedSpeakingFrame to InterruptionTaskFrame."""
        await super().process_frame(frame, direction)
        
        # Check if this is a UserStartedSpeakingFrame that should trigger interruption
        if isinstance(frame, UserStartedSpeakingFrame):
            logger.info(f"🛑 InterruptionConverter: Converting UserStartedSpeakingFrame to InterruptionTaskFrame!")
            
            # Create an InterruptionTaskFrame to trigger TTS interruption
            interruption_frame = InterruptionTaskFrame()
            
            # Push the interruption frame upstream to the task handler
            # This will be converted to InterruptionFrame by PipelineTask and sent to TTS processors
            await self.push_frame(interruption_frame, FrameDirection.UPSTREAM)
            logger.info(f"✅ InterruptionConverter: Sent InterruptionTaskFrame upstream - TTS should stop!")
            
            # Also pass through the original UserStartedSpeakingFrame
            await self.push_frame(frame, direction)
        else:
            # For all other frames, just pass them through
            await self.push_frame(frame, direction)
