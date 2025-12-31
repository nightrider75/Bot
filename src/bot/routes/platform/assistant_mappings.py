"""Platform-facing UI endpoint for assistant mappings."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from bot.routes.platform.templates import render_template

router = APIRouter()


@router.get("/ui", response_class=HTMLResponse)
async def assistant_mappings_page():
    """Serve the assistant mappings admin UI."""
    return render_template(
        "assistant_mappings.html",
        context={"page_title": "Assistant Mappings"},
    )
