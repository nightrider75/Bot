"""Platform root routes for serving HTML pages and static files."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

from bot.routes.platform.templates import (
    inject_asset_types,
    render_template,
)

router = APIRouter()


@router.get("/")
async def index_page():
    """Serve the platform index page.

    Returns:
        HTMLResponse with the platform index page
    """
    return render_template("index.html")


@router.get("/test/websocket")
async def test_websocket():
    """Serve the WebSocket testing page for bot testing.

    Returns:
        HTMLResponse with the WebSocket test interface
    """
    return render_template("websocket_test.html")


@router.get("/test/webrtc")
async def test_webrtc():
    """Serve the WebRTC testing page for bot testing.

    Returns:
        HTMLResponse with the WebRTC test interface
    """
    return render_template("webrtc_test.html")


@router.get("/assets")
async def upload_assets_page():
    """Serve the platform asset upload page.

    Returns:
        HTMLResponse with the asset upload interface, with AssetType values injected
    """
    template_path = Path(__file__).parent / "templates" / "upload_assets.html"

    with open(template_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    # Inject AssetType values into the HTML
    html_content = inject_asset_types(html_content)

    return HTMLResponse(html_content)


@router.get("/static/protobuf_definitions/frames.proto")
async def serve_protobuf():
    """Serve the protobuf schema file."""
    # Get the path to the protobuf file
    proto_file_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "deps"
        / "bot-engine"
        / "src"
        / "bot_engine"
        / "frames"
        / "frames.proto"
    )

    if not proto_file_path.exists():
        return HTMLResponse("Protobuf file not found", status_code=404)

    return FileResponse(
        path=proto_file_path, media_type="text/plain", filename="frames.proto"
    )
