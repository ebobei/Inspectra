from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.logging import configure_logging

configure_logging()


def _validate_security_settings() -> None:
    if settings.app_env.lower() == "production":
        if settings.encryption_key == "change-me-change-me-change-me":
            raise RuntimeError("ENCRYPTION_KEY must be changed in production")
        if settings.admin_api_token == "change-me-admin-token":
            raise RuntimeError("ADMIN_API_TOKEN must be changed in production")


_validate_security_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

allowed_origins = [origin.strip() for origin in settings.ui_allowed_origins.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Inspectra-Admin-Token", "X-Inspectra-Webhook-Secret"],
    )

app.include_router(api_router)
