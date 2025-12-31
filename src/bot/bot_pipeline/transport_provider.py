from typing import Any

from fastapi import WebSocket
from bot_engine.audio.vad.silero import SileroVADAnalyzer
from bot_engine.audio.vad.vad_analyzer import VADParams
from bot_engine.transports.smallwebrtc.transport import SmallWebRTCTransport
from bot_engine.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from bot.config import settings
from bot.types import StreamConfig, TransportConfig, TransportType


class TransportProvider:
    @classmethod
    def get_provider(
        cls,
        transport_config: TransportConfig,
        stream_config: StreamConfig,
        connection: WebSocket | Any,
    ):
        # Control mixer settings
        # Use more lenient VAD parameters for websocket transport
        if transport_config.provider == TransportType.BOT_WEBSOCKET:
            # Very lenient VAD settings for websocket testing
            vad_params = VADParams(
                confidence=0.3,  # Even lower confidence threshold
                stop_secs=1.0,  # Longer silence to stop
                start_secs=0.1,  # Very short voice to start
                min_volume=0.05,  # Very low volume threshold
            )
        else:
            # Use configured VAD parameters for other transports
            vad_params = VADParams(
                confidence=transport_config.vad_params.confidence_threshold,
                stop_secs=transport_config.vad_params.stop_secs,
                start_secs=transport_config.vad_params.start_secs,
                min_volume=transport_config.vad_params.volume_threshold,
            )
        transport_param = FastAPIWebsocketParams(
            audio_out_enabled=True,
            add_wav_header=False,
            audio_in_enabled=transport_config.vad_params.enabled,
            vad_analyzer=SileroVADAnalyzer(params=vad_params),
            audio_in_passthrough=True,
            session_timeout=transport_config.session_timeout,
        )
        if transport_config.provider == TransportType.WEBRTC:
            return SmallWebRTCTransport(
                params=transport_param, webrtc_connection=connection
            )
        else:
            if transport_config.provider == TransportType.TWILIO:
                from bot_engine.serializers.twilio import TwilioFrameSerializer

                transport_param.serializer = TwilioFrameSerializer(
                    stream_sid=stream_config.stream_id,
                    call_sid=stream_config.call_id,
                    account_sid=stream_config.account_id,
                    auth_token=settings.telephony_config.twilio.auth_token,
                )
            elif transport_config.provider == TransportType.OZONOTEL:
                raise NotImplementedError("Ozonetel transport not implemented yet")
            elif transport_config.provider == TransportType.TELNYX:
                from bot_engine.serializers.telnyx import TelnyxFrameSerializer

                transport_param.serializer = TelnyxFrameSerializer(
                    stream_id=stream_config.stream_id,
                    call_control_id=stream_config.call_id,
                    outbound_encoding=stream_config.outbound_encoding,
                    inbound_encoding="PCMU",  # Standard default
                    api_key=settings.transport_credentials.telnyx_api_key,
                )
            elif transport_config.provider == TransportType.EXOTEL:
                from bot_engine.serializers.exotel import ExotelFrameSerializer

                transport_param.serializer = ExotelFrameSerializer(
                    stream_id=stream_config.stream_id,
                    call_id=stream_config.call_id,
                )
            elif transport_config.provider == TransportType.PLIVO:
                from bot_engine.serializers.plivo import PlivoFrameSerializer

                transport_param.serializer = PlivoFrameSerializer(
                    stream_id=stream_config.stream_id,
                    call_id=stream_config.call_id,
                    auth_id=settings.telephony_config.plivo.auth_id,
                    auth_token=settings.telephony_config.plivo.auth_token,
                )
            elif transport_config.provider == TransportType.BOT_WEBSOCKET:
                from bot.transports.websocket_transport import (
                    WebSocketFrameSerializer,
                )

                # Use the existing FastAPIWebsocketTransport with our custom serializer
                transport_param.serializer = WebSocketFrameSerializer()
            elif transport_config.provider == TransportType.ASTERISK:
                from bot_engine.serializers.asterisk import (
                    AsteriskFrameSerializer,
                )

                transport_param.serializer = AsteriskFrameSerializer(
                    stream_config.stream_id
                )
                transport_param.audio_out_10ms_chunks = 2
            else:
                raise ValueError(f"Unknown transport type: {transport_config}")

            return FastAPIWebsocketTransport(
                websocket=connection, params=transport_param
            )
