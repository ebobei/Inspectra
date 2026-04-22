from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db


def db_dependency() -> Session:
    return next(get_db())


def require_admin_token(x_inspectra_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_api_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin API token is not configured")
    if x_inspectra_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API token")


AdminTokenDependency = Depends(require_admin_token)
