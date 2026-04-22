from fastapi import HTTPException, Request, status

from app.config import settings


class SecurityService:
    def verify_webhook_secret(self, request: Request) -> None:
        configured = settings.webhook_shared_secret
        if not configured:
            return

        provided = request.headers.get("x-inspectra-webhook-secret")
        if provided != configured:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret",
            )
