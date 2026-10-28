from fastapi import APIRouter

from app.modules.health.router import router as health_router
from app.modules.conversations.router import router as conversations_router
from app.modules.platform.router import router as platform_router
from app.modules.widget.router import router as widget_router
from app.modules.platform.institution import router as institution_router, public_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(platform_router, prefix="/v1")
api_router.include_router(conversations_router, prefix="/v1")
api_router.include_router(widget_router, prefix="/v1")
api_router.include_router(institution_router, prefix="/v1")
api_router.include_router(public_router, prefix="/v1")
