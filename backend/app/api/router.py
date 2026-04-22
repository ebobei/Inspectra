from fastapi import APIRouter, Depends

from app.api import admin, connectors, health, publications, reviews, sessions, webhooks
from app.dependencies import require_admin_token

protected = [Depends(require_admin_token)]

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(sessions.router, dependencies=protected)
api_router.include_router(reviews.router, dependencies=protected)
api_router.include_router(publications.router, dependencies=protected)
api_router.include_router(connectors.router, dependencies=protected)
api_router.include_router(admin.router, dependencies=protected)
api_router.include_router(webhooks.router)
