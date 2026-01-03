from typing import Dict, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, WebSocket
from fastapi.responses import PlainTextResponse, Response
from loguru import logger
from plivo import RestClient as PlivoClient
from plivo import plivoxml
from pydantic import BaseModel, Field
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse
from bot_engine.runner.utils import parse_telephony_websocket
from bot_engine.transports.smallwebrtc.connection import (
    IceServer,
    SmallWebRTCConnection,
)

from bot.bot_hub.hub import BotHub
from bot.bot_pipeline.runner import run_bot
from bot.config import settings
from bot.types import StreamConfig, TransportType

router = APIRouter()


class OutboundCallRequest(BaseModel):
    """Request model for triggering outbound calls."""

    phone_number: str = Field(
        ...,
        description="The destination phone number to call (E.164 format recommended, e.g., +1234567890)",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user ID to associate with this call. If not provided, phone number will be used.",
    )


class OutboundCallResponse(BaseModel):
    """Response model for outbound call requests."""

    success: bool
    message: str
    call_sid: Optional[str] = None
    call_status: Optional[str] = None


class WebRTCOfferRequest(BaseModel):
    """Request model for WebRTC offer."""

    sdp: str = Field(..., description="The SDP offer from the client")
    type: str = Field(..., description="The SDP type (usually 'offer')")
    pc_id: Optional[str] = Field(
        default=None, description="Optional peer connection ID for renegotiation"
    )
    user_id: Optional[str] = Field(
        default="webrtc_user", description="User ID for the session"
    )
    voice_id: Optional[str] = Field(
        default=None, description="Optional TTS voice_id override for accent selection"
    )
    language: Optional[str] = Field(
        default=None,
        description="Optional language code for multilingual support (e.g., 'hi' for Hindi, 'de' for German). When set, the bot will respond in this language.",
    )


# Plivo Integration


@router.post("/{bot_id}/plivo/outbound/call", response_model=OutboundCallResponse)
async def trigger_plivo_outbound_call(bot_id: UUID, request: OutboundCallRequest):
    """
    Trigger an outbound call using Plivo.

    Args:
        bot_id: The bot identifier to use for the call
        request: OutboundCallRequest containing phone_number and optional user_id

    Returns:
        OutboundCallResponse with call status and details
    """
    with logger.contextualize(bot_id=bot_id, telephony="plivo-outbound"):
        try:
            # Validate Plivo configuration
            if not all(
                [
                    settings.telephony_config.plivo.auth_id,
                    settings.telephony_config.plivo.auth_token,
                    settings.telephony_config.plivo.phone_number,
                ]
            ):
                raise HTTPException(
                    status_code=500,
                    detail="Plivo credentials not configured. Please check TELEPHONY_CONFIG__PLIVO__AUTH_ID, TELEPHONY_CONFIG__PLIVO__AUTH_TOKEN, and TELEPHONY_CONFIG__PLIVO__PHONE_NUMBER in settings.",
                )

            # Initialize Plivo client
            client = PlivoClient(
                auth_id=settings.telephony_config.plivo.auth_id,
                auth_token=settings.telephony_config.plivo.auth_token,
            )

            # Construct the callback URL for this bot
            callback_url = f"https://{settings.base_url_domain}/api/v1/transport/{bot_id}/plivo/incoming_call"

            logger.info(
                f"Initiating Plivo outbound call to {request.phone_number} with callback URL: {callback_url}"
            )

            # Create the call
            response = client.calls.create(
                from_=settings.telephony_config.plivo.phone_number,
                to_=request.phone_number,
                answer_url=callback_url,
                answer_method="POST",
            )

            # Plivo response is a ResponseObject with attributes
            logger.info(
                f"Plivo outbound call initiated successfully. Request UUID: {response.request_uuid}, Message: {response.message}"
            )

            return OutboundCallResponse(
                success=True,
                message="Outbound call initiated successfully",
                call_sid=response.request_uuid,
                call_status=response.message,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to initiate Plivo outbound call: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initiate outbound call: {str(e)}",
            )


@router.get("/{bot_id}/plivo/incoming_call")
@router.post("/{bot_id}/plivo/incoming_call")
async def plivo_sample(request: Request, bot_id: UUID):
    """
    Returns the XML response for Plivo to initiate streaming.
    The XML will contain the WebSocket URL with the necessary parameters.
    """
    with logger.contextualize(bot_id=bot_id, telephony="plivo"):
        caller = "unknown"
        account_id = "unknown"
        try:
            # Try to parse form data
            form_data = await request.form()
            logger.info(f"Plivo Form data received: {dict(form_data)}")
            form_data = dict(form_data)
            if form_data.get("Direction", "") == "outbound":
                caller = form_data.get("To", "").strip("+")
            else:
                caller = form_data.get("From", "").strip("+")
            account_id = form_data.get("ParentAuthID")
        except Exception as e:
            logger.error(f"Error decoding plivo form: {str(e)}")

        headers = {"user_id": caller, "account_id": account_id}
        extra_headers = ",".join(f"{k}={v}" for k, v in headers.items())

        response = plivoxml.ResponseElement()
        response.add(
            plivoxml.RecordElement(
                action=f"https://{settings.base_url_domain}/api/v1/transport/{bot_id}/plivo/action",
                redirect=False,
                max_length=3600,
                record_session=True,
                callback_url=f"https://{settings.base_url_domain}/api/v1/transport/{bot_id}/plivo/callback",
            )
        )
        response.add(
            plivoxml.StreamElement(
                f"wss://{settings.base_url_domain}/api/v1/transport/{bot_id}/plivo/ws",
                streamTimeout=3600,
                keepCallAlive=True,
                bidirectional=True,
                audioTrack="inbound",
                contentType="audio/x-mulaw;rate=8000",
                statusCallbackUrl=f"https://{settings.base_url_domain}/api/v1/transport/{bot_id}/plivo/callback",
                statusCallbackMethod="POST",
                extraHeaders=extra_headers,
            )
        )
        return Response(content=response.to_string(), media_type="application/xml")


@router.get("/{bot_id}/plivo/action")
@router.post("/{bot_id}/plivo/action")
async def plivo_action(request: Request, bot_id: UUID):
    """
    Endpoint to receive Plivo call status callbacks.
    Here you can check the CallStatus to see if the call was not answered.
    """
    return {}


@router.get("/{bot_id}/plivo/callback")
@router.post("/{bot_id}/plivo/callback")
async def plivo_callback(request: Request, bot_id: UUID):
    """
    Endpoint to receive Plivo call status callbacks.
    Here you can check the CallStatus to see if the call was not answered.
    """
    return {}


@router.websocket("/{bot_id}/plivo/ws")
async def plivo_websocket_endpoint(websocket: WebSocket, bot_id: UUID):
    await websocket.accept()
    session_id = uuid4()
    with logger.contextualize(bot_id=bot_id, session_id=session_id, telephony="plivo"):
        telephony, call_data = await parse_telephony_websocket(websocket)
        logger.debug(
            f"Received Plivo WebSocket connection provider: {telephony} : {call_data}"
        )
        stream_config = StreamConfig(
            stream_id=call_data.get("stream_id"),
            call_id=call_data.get("call_id"),
            account_id=call_data.get("body", {}).get("account_sid"),
            user_id=call_data.get("body", {}).get("user_id"),
            outbound_encoding="PCMU",
            bot_session_id=session_id,
            host_id=settings.host_id,
        )
        with logger.contextualize(
            stream_id=stream_config.stream_id,
            call_id=stream_config.call_id,
            account_id=stream_config.account_id,
        ):
            await run_bot(
                transport_type=TransportType.PLIVO,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
            )


# TWILIO INTEGRATION


@router.post("/{bot_id}/twilio/outbound/call", response_model=OutboundCallResponse)
async def trigger_twilio_outbound_call(bot_id: UUID, request: OutboundCallRequest):
    """
    Trigger an outbound call using Twilio.

    Args:
        bot_id: The bot identifier to use for the call
        request: OutboundCallRequest containing phone_number and optional user_id

    Returns:
        OutboundCallResponse with call status and details
    """
    with logger.contextualize(bot_id=bot_id, telephony="twilio-outbound"):
        try:
            # Validate Twilio configuration
            if not all(
                [
                    settings.telephony_config.twilio.account_sid,
                    settings.telephony_config.twilio.auth_token,
                    settings.telephony_config.twilio.phone_number,
                ]
            ):
                raise HTTPException(
                    status_code=500,
                    detail="Twilio credentials not configured. Please check TELEPHONY_CONFIG__TWILIO__ACCOUNT_SID, TELEPHONY_CONFIG__TWILIO__AUTH_TOKEN, and TELEPHONY_CONFIG__TWILIO__PHONE_NUMBER in settings.",
                )

            # Initialize Twilio client
            client = TwilioClient(
                settings.telephony_config.twilio.account_sid,
                settings.telephony_config.twilio.auth_token,
            )

            # Construct the callback URL for this bot
            callback_url = f"https://{settings.base_url_domain}/api/v1/transport/{bot_id}/twilio/incoming_call"

            logger.info(
                f"Initiating Twilio outbound call to {request.phone_number} with callback URL: {callback_url}"
            )

            # Create the call
            call = client.calls.create(
                to=request.phone_number,
                from_=settings.telephony_config.twilio.phone_number,
                url=callback_url,
                method="POST",
            )

            logger.info(
                f"Twilio outbound call initiated successfully. Call SID: {call.sid}, Status: {call.status}"
            )

            return OutboundCallResponse(
                success=True,
                message="Outbound call initiated successfully",
                call_sid=call.sid,
                call_status=call.status,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to initiate Twilio outbound call: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initiate outbound call: {str(e)}",
            )


@router.post("/{bot_id}/incoming_call/twilio")
@router.post("/{bot_id}/twilio/incoming_call")
async def incoming_call(request: Request, bot_id: UUID):
    """
    Twilio hits this endpoint to get instructions after the inbound call is answered.
    We instruct Twilio to start streaming to the same WebSocket endpoint.
    """
    form = dict(await request.form())

    # logger.debug(f"Incoming Twilio call with body: {body} and form: {form}")
    if form.get("Direction") == "inbound":
        user_id = form.get("From")
    else:
        user_id = form.get("To")
    account_sid = form.get("AccountSid")

    resp = VoiceResponse()
    stream = Stream(
        url=f"wss://{settings.base_url_domain}/api/v1/transport/{bot_id}/twilio/ws"
    )
    stream.parameter(name="user_id", value=user_id)
    stream.parameter(name="account_sid", value=account_sid)
    connect = Connect()
    connect.append(stream)
    resp.append(connect)

    return PlainTextResponse(str(resp), media_type="application/xml")


@router.websocket("/{bot_id}/twilio/ws")
async def twilio_websocket_endpoint(websocket: WebSocket, bot_id: UUID):
    await websocket.accept()
    session_id = uuid4()
    with logger.contextualize(bot_id=bot_id, session_id=session_id, telephony="twilio"):
        telephony, call_data = await parse_telephony_websocket(websocket)
        logger.debug(
            f"Received Twilio WebSocket connection provider: {telephony} : {call_data}"
        )
        stream_config = StreamConfig(
            stream_id=call_data.get("stream_id"),
            call_id=call_data.get("call_id"),
            account_id=call_data.get("body", {}).get("account_sid"),
            user_id=call_data.get("body", {}).get("user_id"),
            outbound_encoding="PCMU",
            bot_session_id=session_id,
            host_id=settings.host_id,
        )
        with logger.contextualize(
            stream_id=stream_config.stream_id,
            call_id=stream_config.call_id,
            account_id=stream_config.account_id,
        ):
            await run_bot(
                transport_type=TransportType.TWILIO,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
            )


# Twilio SIP Integration


@router.post("/{bot_id}/twilio/sip/incoming_call")
async def incoming_call_sip(request: Request, bot_id: UUID):
    """
    This endpoint is hit when someone calls your Twilio number.
    We return TwiML that instructs Twilio to start streaming the call audio
    to our WebSocket endpoint.
    """
    resp = VoiceResponse()
    form_data = await request.form()

    if form_data.get("Direction") == "inbound":
        user_id = form_data.get("From")
    else:
        user_id = form_data.get("To")
    account_sid = form_data.get("AccountSid")
    sip_user_tou = form_data.get("SipHeader_User-to-User")
    from_number = form_data.get("SipHeader_from_number")
    stream = Stream(
        url=f"wss://{settings.base_url_domain}/api/v1/transport/{bot_id}/twilio/sip/ws"
    )

    tpcode = ""
    phone_number_from_tpiid = ""
    if sip_user_tou:
        try:
            # Extract hex part (remove ;encoding=hex if present)
            hex_part = (
                sip_user_tou.split(";")[0] if ";" in sip_user_tou else sip_user_tou
            )
            logger.info(f"Hex part: {hex_part}")

            # Decode from hex
            decoded_sipusertou = bytes.fromhex(hex_part).decode("utf-8")
            logger.info(f"Decoded sipusertou: {decoded_sipusertou}")

            # Split by pipe - left is tpcode, right is phone number
            if "|" in decoded_sipusertou:
                parts = decoded_sipusertou.split("|", 1)
                tpcode = parts[0]
                phone_number_from_tpiid = parts[1]
                # tpiid = decoded_sipusertou  # The full decoded string
                logger.info(
                    f"Extracted tpcode: {tpcode}, phone_number: {phone_number_from_tpiid}"
                )
            else:
                logger.warning(
                    f"No pipe separator found in decoded sipusertou: {decoded_sipusertou}"
                )
                # tpiid = decoded_sipusertou
        except ValueError as e:
            logger.error(f"Error decoding sipusertou from hex: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing sipusertou: {e}")

    # Determine the final user_id to use for warmup
    final_user_id = tpcode or user_id

    stream.parameter(name="SIPUSERTOU", value=sip_user_tou)
    stream.parameter(name="from_number", value=from_number)
    stream.parameter(name="user_id", value=final_user_id)
    stream.parameter(name="account_sid", value=account_sid)
    connect = Connect()
    connect.append(stream)
    resp.append(connect)
    return PlainTextResponse(str(resp), media_type="application/xml")


@router.websocket("/{bot_id}/twilio/sip/ws/")
async def twilio_websocket_endpoint_sip(websocket: WebSocket, bot_id: UUID):
    await websocket.accept()
    session_id = uuid4()
    with logger.contextualize(bot_id=bot_id, session_id=session_id, telephony="twilio"):
        telephony, call_data = await parse_telephony_websocket(websocket)
        logger.debug(
            f"Received Twilio WebSocket connection provider: {telephony} : {call_data}"
        )
        # from_number = call_data.get("body", {}).get("from_number")
        stream_config = StreamConfig(
            stream_id=call_data.get("stream_id"),
            call_id=call_data.get("call_id"),
            account_id=call_data.get("body", {}).get("account_sid"),
            user_id=call_data.get("body", {}).get("user_id"),
            outbound_encoding="PCMU",
            bot_session_id=session_id,
            host_id=settings.host_id,
        )
        with logger.contextualize(
            stream_id=stream_config.stream_id,
            call_id=stream_config.call_id,
            account_id=stream_config.account_id,
        ):
            await run_bot(
                transport_type=TransportType.TWILIO,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
            )


# BOT WEBSOCKET INTEGRATION


@router.websocket("/{bot_id}/bot/ws")
async def bot_websocket_endpoint(websocket: WebSocket, bot_id: UUID):
    """
    WebSocket endpoint for local bot testing using bot transport.
    This endpoint accepts WebSocket connections with protobuf-encoded audio frames.
    """
    await websocket.accept()
    session_id = uuid4()

    with logger.contextualize(
        bot_id=bot_id, session_id=session_id, transport="bot_websocket"
    ):
        logger.info("Bot WebSocket connection established")

        try:
            # Get query parameters
            query_params = dict(websocket.query_params)
            user_id = query_params.get("user_id", "test_user")

            # Create stream configuration
            stream_config = StreamConfig(
                stream_id=f"bot_ws_{session_id}",
                call_id=f"bot_call_{session_id}",
                account_id="bot_test",
                outbound_encoding="PCM",  # Use PCM for WebSocket
                user_id=user_id,
                bot_session_id=session_id,
                host_id="bot_test_host",
            )

            # Run the bot with bot WebSocket transport
            await run_bot(
                transport_type=TransportType.BOT_WEBSOCKET,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
            )

        except Exception as e:
            logger.error(f"Error in bot WebSocket endpoint: {str(e)}")
            await websocket.close(code=1011, reason="Internal server error")


# WebRTC INTEGRATION

# Configure ICE servers with both STUN and TURN for reliable NAT traversal
# STUN server helps discover public IP addresses
# TURN server relays traffic when direct peer-to-peer connection fails
ice_servers = [
    IceServer(
        urls="stun:stun.l.google.com:19302",
    ),
    IceServer(
        urls="turn:openrelay.metered.ca:80",
        username="openrelayproject",
        credential="openrelayproject",
    ),
]

# Store connections by pc_id
connections_map: Dict[str, SmallWebRTCConnection] = {}


@router.post("/{bot_id}/webrtc/offer")
async def offer(
    request: WebRTCOfferRequest, background_tasks: BackgroundTasks, bot_id: UUID
):
    pc_id = request.pc_id
    user_id = request.user_id
    session_id = uuid4()

    with logger.contextualize(bot_id=bot_id, session_id=session_id, transport="webrtc"):
        logger.info(f"WebRTC offer received for user: {user_id}")

        if pc_id and pc_id in connections_map:
            connection = connections_map[pc_id]
            logger.info(f"Reusing existing connection for pc_id: {pc_id}")
            await connection.renegotiate(sdp=request.sdp, type=request.type)
        else:
            connection = SmallWebRTCConnection(ice_servers)
            await connection.initialize(sdp=request.sdp, type=request.type)

            @connection.event_handler("closed")
            async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
                logger.info(
                    f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}"
                )
                connections_map.pop(webrtc_connection.pc_id, None)

            # Create stream configuration for WebRTC
            stream_config = StreamConfig(
                stream_id=f"webrtc_{session_id}",
                call_id=f"webrtc_call_{session_id}",
                account_id="webrtc_test",
                user_id=user_id,  # Use dynamic user_id from request
                outbound_encoding="PCM",  # Use PCM for WebRTC
                bot_session_id=session_id,
                host_id=settings.host_id,
            )

            # Initialize BotHub and user data for WebRTC (similar to other transports)
            bot_hub = BotHub(bot_id)

            # Create user data for WebRTC
            from bot.bot_hub.types import BotUserData

            webrtc_user_data = {
                "user_id": user_id,
                "transport": "webrtc",
                "session_id": str(session_id),
            }
            await bot_hub.userdata_provider.add_user_data(
                [BotUserData(user_id=stream_config.user_id, data=webrtc_user_data)]
            )

            # Create a wrapper function to handle cleanup
            async def run_bot_with_cleanup():
                try:
                    await run_bot(
                        transport_type=TransportType.WEBRTC,
                        stream_config=stream_config,
                        connection=connection,
                        bot_identifier=bot_id,
                        voice_id_override=request.voice_id,
                        language_override=request.language,
                    )
                finally:
                    # Clean up user data when bot session ends
                    await bot_hub.userdata_provider.delete_user_data(
                        stream_config.user_id
                    )
                    logger.info(
                        f"Cleaned up user data for user: {stream_config.user_id}"
                    )

            # Run bot with proper cleanup
            background_tasks.add_task(run_bot_with_cleanup)

        answer = connection.get_answer()
        # Updating the peer connection inside the map
        connections_map[answer["pc_id"]] = connection

        return answer


@router.websocket("/{bot_id}/asterisk/ws")
async def asterisk_websocket(websocket: WebSocket, bot_id: UUID):
    websocket_params = dict(websocket.query_params)
    logger.debug(f"Asterisk query params: {websocket_params}")

    await websocket.accept()
    session_id = uuid4()
    user_id = str(uuid4())
    stream_id = str(uuid4())
    with logger.contextualize(
        bot_id=bot_id, session_id=session_id, telephony="asterisk"
    ):
        stream_config = StreamConfig(
            user_id=user_id,
            stream_id=stream_id,
            outbound_encoding="PCMU",
            bot_session_id=session_id,
            host_id=settings.host_id,
        )
        with logger.contextualize(
            stream_id=stream_config.stream_id,
            call_id=stream_config.call_id,
            account_id=stream_config.account_id,
        ):
            await run_bot(
                transport_type=TransportType.ASTERISK,
                stream_config=stream_config,
                connection=websocket,
                bot_identifier=bot_id,
            )
