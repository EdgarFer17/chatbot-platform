from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.rate_limit import public_rate_limit


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API multi-instituição para assistentes com conhecimento controlado.",
        generate_unique_id_function=lambda route: route.name if isinstance(route, APIRoute) else route.name,
        contact={"name": "Chatbot Platform"},
        license_info={"name": "Proprietary"},
        lifespan=lifespan,
    )
    application.middleware("http")(public_rate_limit)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Admin-Key"],
    )
    application.include_router(api_router)
    return application


app = create_app()
