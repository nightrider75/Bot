"""Platform routes for bot management."""

from uuid import UUID

from fastapi import APIRouter

from bot.routes.platform.templates import render_template

router = APIRouter()


@router.get("/bot/{bot_id}")
async def bot_hub_page(bot_id: UUID):
    """Serve the bot hub page for managing bot nodes.

    Args:
        bot_id: UUID of the bot

    Returns:
        HTMLResponse with the bot hub interface
    """
    return render_template("bot.html")
