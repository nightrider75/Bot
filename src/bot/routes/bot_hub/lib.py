from fastapi import APIRouter

# Import bot hub sub-routers
from bot.routes.bot_hub.bot import router as bot_router
from bot.routes.bot_hub.config import router as config_router
from bot.routes.bot_hub.functions import (
    router as functions_router,
)
from bot.routes.bot_hub.nodes import router as nodes_router
from bot.routes.bot_hub.userdata import router as userdata_router

router = APIRouter()

# Include sub-routers related to bot level configuration
router.include_router(bot_router, tags=["Bot Hub - Bots"])
router.include_router(nodes_router, tags=["Bot Hub - Nodes"])
router.include_router(userdata_router, tags=["Bot Hub - User Data"])
router.include_router(functions_router, tags=["Bot Hub - Functions"])
router.include_router(config_router, tags=["Bot Hub - Config"])
