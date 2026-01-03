"""WebSocket transport implementation for local bot testing.

This module provides a WebSocket-based transport for testing bots locally
using protobuf serialization for audio frames.
"""

import logging

from bot_engine.frames.frames import (
    AudioRawFrame,
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
)
from bot_engine.serializers.base_serializer import (
    FrameSerializer,
    FrameSerializerType,
)

logger = logging.getLogger(__name__)


class WebSocketFrameSerializer(FrameSerializer):
    """Serializer for WebSocket frames using protobuf."""

    def __init__(self):
        self._frame_type = None
        self._load_protobuf()

    def _load_protobuf(self):
        """Load the protobuf Frame type from bot-engine."""
        # NOTE:
        # The checked-in/generated `frames_pb2.py` currently fails at import-time with:
        #   TypeError: Couldn't parse file content!
        # which indicates a protobuf runtime / generated-code mismatch.
        # Until that is fixed, we force the binary fallback format to keep the
        # WebSocket transport usable from browsers.
        self._frame_type = None
        self._audio_type = None
        logger.warning(
            "Protobuf framing is disabled; using binary fallback framing for WebSocket audio"
        )

    def _create_frame_type(self):
        """Create a simple frame type for testing."""

        # This is a simplified implementation
        # In production, you'd use the compiled protobuf
        class SimpleFrame:
            def __init__(self, audio_data=None, sample_rate=24000, num_channels=1):
                self.audio_data = audio_data or b""
                self.sample_rate = sample_rate
                self.num_channels = num_channels

            def SerializeToString(self):
                # Simple binary format: [4 bytes sample_rate][4 bytes num_channels][audio_data]
                import struct

                header = struct.pack("<II", self.sample_rate, self.num_channels)
                return header + self.audio_data

            def ParseFromString(self, data):
                """Parse binary data back to frame."""
                if len(data) < 8:
                    raise ValueError("Invalid frame data")

                import struct

                self.sample_rate, self.num_channels = struct.unpack("<II", data[:8])
                self.audio_data = data[8:]
                return self

        return SimpleFrame

    @property
    def type(self) -> FrameSerializerType:
        """Get the serialization type supported by this serializer."""
        return FrameSerializerType.BINARY

    async def serialize(self, frame: Frame) -> str | bytes | None:
        """Convert a frame to its serialized representation."""
        if isinstance(frame, (InputAudioRawFrame, OutputAudioRawFrame, AudioRawFrame)):
            return self.serialize_audio_frame(frame)
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        """Convert serialized data back to a frame object."""
        if isinstance(data, bytes):
            return self.deserialize_audio_frame(data)
        return None

    def serialize_audio_frame(self, frame: AudioRawFrame) -> bytes:
        """Serialize an audio frame to bytes."""
        if self._frame_type and hasattr(self, "_audio_type") and self._audio_type:
            try:
                # Use proper protobuf format with the new structure
                audio_msg = self._audio_type(
                    id=getattr(frame, "id", 0),
                    name=getattr(frame, "name", "audio"),
                    audio=frame.audio,
                    sample_rate=frame.sample_rate,
                    num_channels=frame.num_channels,
                    pts=getattr(frame, "pts", None),
                )
                proto_frame = self._frame_type()
                proto_frame.audio.CopyFrom(audio_msg)
                return proto_frame.SerializeToString()
            except Exception as e:
                logger.warning(f"Protobuf serialization failed: {e}, using fallback")
                # Fall through to fallback
        elif self._frame_type:
            try:
                # Fallback to simple frame type
                proto_frame = self._frame_type(
                    audio_data=frame.audio,
                    sample_rate=frame.sample_rate,
                    num_channels=frame.num_channels,
                )
                return proto_frame.SerializeToString()
            except Exception as e:
                logger.warning(
                    f"Simple frame serialization failed: {e}, using binary fallback"
                )
                # Fall through to binary fallback

        # Final fallback: simple binary format
        import struct

        header = struct.pack("<II", frame.sample_rate, frame.num_channels)
        return header + frame.audio

    def deserialize_audio_frame(self, data: bytes) -> InputAudioRawFrame:
        """Deserialize bytes to an audio frame."""
        if self._frame_type and hasattr(self, "_audio_type") and self._audio_type:
            # Use proper protobuf format with the new structure
            try:
                # Validate data before parsing to prevent division by zero
                if not data or len(data) < 4:
                    raise ValueError("Invalid protobuf data: too short")

                # Check for potential division by zero in protobuf parsing
                # by validating the data structure first
                proto_frame = self._frame_type()
                proto_frame.ParseFromString(data)

                # Check which frame type we have (using oneof)
                if proto_frame.HasField("audio"):
                    audio_msg = proto_frame.audio

                    # Validate audio message fields to prevent division by zero
                    if audio_msg.sample_rate <= 0:
                        # Only log once to avoid spam
                        if not hasattr(self, "_logged_invalid_sample_rate"):
                            logger.warning(
                                f"Invalid sample rate: {audio_msg.sample_rate}, using default 24000"
                            )
                            self._logged_invalid_sample_rate = True
                        sample_rate = 24000
                    else:
                        sample_rate = audio_msg.sample_rate

                    if audio_msg.num_channels <= 0:
                        # Only log once to avoid spam
                        if not hasattr(self, "_logged_invalid_channels"):
                            logger.warning(
                                f"Invalid num_channels: {audio_msg.num_channels}, using default 1"
                            )
                            self._logged_invalid_channels = True
                        num_channels = 1
                    else:
                        num_channels = audio_msg.num_channels

                    return InputAudioRawFrame(
                        audio=audio_msg.audio,
                        sample_rate=sample_rate,
                        num_channels=num_channels,
                    )
                else:
                    raise ValueError("No audio data in protobuf frame")
            except Exception as e:
                logger.warning(f"Error parsing protobuf frame: {e}, trying fallback")
                # Fall through to fallback
        elif self._frame_type:
            try:
                # Fallback to simple frame type
                if not data or len(data) < 8:
                    raise ValueError("Invalid simple frame data: too short")

                proto_frame = self._frame_type()
                proto_frame.ParseFromString(data)

                # Validate fields to prevent division by zero
                if proto_frame.sample_rate <= 0:
                    if not hasattr(self, "_logged_simple_invalid_sample_rate"):
                        logger.warning(
                            f"Simple frame: Invalid sample rate: {proto_frame.sample_rate}, using default 24000"
                        )
                        self._logged_simple_invalid_sample_rate = True
                    sample_rate = 24000
                else:
                    sample_rate = proto_frame.sample_rate

                if proto_frame.num_channels <= 0:
                    if not hasattr(self, "_logged_simple_invalid_channels"):
                        logger.warning(
                            f"Simple frame: Invalid num_channels: {proto_frame.num_channels}, using default 1"
                        )
                        self._logged_simple_invalid_channels = True
                    num_channels = 1
                else:
                    num_channels = proto_frame.num_channels

                return InputAudioRawFrame(
                    audio=proto_frame.audio_data,
                    sample_rate=sample_rate,
                    num_channels=num_channels,
                )
            except Exception as e:
                # Only log the error once to avoid spam
                if not hasattr(self, "_logged_simple_frame_error"):
                    logger.warning(
                        f"Error parsing simple frame: {e}, using binary fallback"
                    )
                    self._logged_simple_frame_error = True
                # Fall through to binary fallback

        # Final fallback: simple binary format
        if len(data) < 8:
            raise ValueError("Invalid frame data")

        import struct

        try:
            sample_rate, num_channels = struct.unpack("<II", data[:8])
        except struct.error as e:
            logger.warning(f"Error unpacking binary data: {e}, using defaults")
            sample_rate = 24000
            num_channels = 1

        audio_data = data[8:]

        # Validate sample rate and channels to prevent division by zero
        if sample_rate <= 0 or sample_rate > 48000:
            if not hasattr(self, "_logged_binary_invalid_sample_rate"):
                logger.warning(
                    f"Binary frame: Invalid sample rate: {sample_rate}, using default 24000"
                )
                self._logged_binary_invalid_sample_rate = True
            sample_rate = 24000  # Default to 24kHz
        if num_channels <= 0 or num_channels > 2:
            if not hasattr(self, "_logged_binary_invalid_channels"):
                logger.warning(
                    f"Binary frame: Invalid num_channels: {num_channels}, using default 1"
                )
                self._logged_binary_invalid_channels = True
            num_channels = 1  # Default to mono

        # Create InputAudioRawFrame with basic parameters only
        # pts and transport_source are set automatically by the frame system
        return InputAudioRawFrame(
            audio=audio_data, sample_rate=sample_rate, num_channels=num_channels
        )
