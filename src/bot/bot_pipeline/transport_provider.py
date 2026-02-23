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
        # Use configured VAD parameters for all transport types
        if transport_config.provider == TransportType.BOT_WEBSOCKET:
            # Use configured VAD params, but apply sensible websocket defaults
            # if no custom config was provided. These defaults are tuned
            # to avoid false interrupts from ambient noise / speaker echo.
            vad_params = VADParams(
                confidence=transport_config.vad_params.confidence_threshold,
                stop_secs=transport_config.vad_params.stop_secs,
                start_secs=max(transport_config.vad_params.start_secs, 0.3),  # At least 300ms to confirm speech
                min_volume=max(transport_config.vad_params.volume_threshold, 0.4),  # At least 0.4 to avoid echo
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
