from fastapi import APIRouter

# Import Platform sub-routers
from bot.routes.platform.assistant_mappings import (
    router as assistant_mappings_ui_router,
)
from bot.routes.platform.auth import router as auth_router
from bot.routes.platform.bot import router as bot_router
from bot.routes.platform.config import router as config_router
from bot.routes.platform.csv_manager import (
    router as userdata_router,
)

# from bot.routes.platform.functions import (
#     router as functions_router,
# )
from bot.routes.platform.nodes import router as nodes_router
from bot.routes.platform.root import router as root_router

# from bot.routes.platform.userdata import router as userdata_router

router = APIRouter()

# Include sub-routers related to providing UI
router.include_router(auth_router, tags=["Platform - Auth"])
router.include_router(bot_router, tags=["Platform - Bots"])
router.include_router(nodes_router, tags=["Platform - Nodes"])
# router.include_router(userdata_router, tags=["Platform - User Data"])
# router.include_router(functions_router, tags=["Platform - Functions"])
router.include_router(config_router, tags=["Platform - Config"])
router.include_router(
    userdata_router, prefix="/csv_manager", tags=["Platform - UserData CSV Manager"]
)
router.include_router(
    assistant_mappings_ui_router,
    prefix="/assistant-mappings",
    tags=["Platform - Assistant Mappings"],
)
# Register root router last as it contains catch-all routes
router.include_router(root_router, tags=["Platform - Root"])
