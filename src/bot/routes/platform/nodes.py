"""Platform routes for node management."""

from uuid import UUID

from fastapi import APIRouter

from bot.routes.platform.templates import render_template

router = APIRouter()


@router.get("/bot/{bot_id}/nodes/{node_id}")
async def prompt_editor(bot_id: UUID, node_id: UUID):
    """Serve the node prompt editor page.

    Args:
        bot_id: UUID of the bot
        node_id: UUID of the node

    Returns:
        HTMLResponse with the prompt editor interface
    """
    return render_template("node_editor.html")


@router.get("/bot/{bot_id}/nodes/{node_id}/functions")
async def functions_integration(bot_id: UUID, node_id: UUID):
    """Serve the node prompt editor page.

    Args:
        bot_id: UUID of the bot
        node_id: UUID of the node

    Returns:
        HTMLResponse with the prompt editor interface
    """
    return render_template("functions.html")
