from fastapi import APIRouter

from bot.routes.platform_admin.assets import (
    router as asset_router,
)
from bot.routes.platform_admin.assistant_mappings import (
    router as assistant_mappings_router,
)

router = APIRouter()

# Include sub-routers related to platform level configuration
router.include_router(asset_router, prefix="/assets", tags=["Assets"])
router.include_router(
    assistant_mappings_router, prefix="/assistant-mappings", tags=["Assistant Mappings"]
)
