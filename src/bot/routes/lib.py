from fastapi import APIRouter, Depends

from bot.auth import get_current_username
from bot.routes.bot_hub.lib import router as bot_hub_router
from bot.routes.platform_admin.lib import (
    router as platform_api_router,
)
from bot.routes.transport import router as transport_router
from bot.routes.bot_outbound_transport import (
    router as bot_outbound_transport,
)
from bot.routes.demo_websocket import router as demo_router

router = APIRouter()

# Apply HTTP Basic Auth to bot_hub and platform routes
router.include_router(
    bot_hub_router,
    prefix="/bot_hub",
    dependencies=[Depends(get_current_username)],
)
router.include_router(
    platform_api_router,
    prefix="/platform",
    dependencies=[Depends(get_current_username)],
)
router.include_router(transport_router, prefix="/transport", tags=["Transport"])
router.include_router(
    bot_outbound_transport,
    prefix="/bot_outbound_transport",
    tags=["Bot Outbound Compatible Transport"],
)
router.include_router(demo_router, tags=["Demo WebSocket"])
