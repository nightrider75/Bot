"""Platform routes for bot configuration management."""

from uuid import UUID

from fastapi import APIRouter

from bot.routes.platform.templates import render_template

router = APIRouter()


@router.get("/bot/{bot_id}/config")
async def config_page(bot_id: UUID):
    """Serve the configuration management page.

    Args:
        bot_id: UUID of the bot

    Returns:
        HTMLResponse with the configuration editor interface
    """
    return render_template("config.html", context={"bot_id": str(bot_id)})
