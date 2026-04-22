from fastapi import APIRouter
from sqlalchemy import text

from app.db import SessionLocal
from app.workers.queue import redis_conn

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def healthcheck() -> dict:
    db_status = "ok"
    redis_status = "ok"

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        redis_conn.ping()
    except Exception:
        redis_status = "error"

    overall_status = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": overall_status,
        "service": "inspectra-backend",
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
        },
    }
