from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.admin import AdminMetricsResponse, QueueStatusResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=AdminMetricsResponse)
def get_metrics(db: Session = Depends(get_db)) -> AdminMetricsResponse:
    return AdminService().get_metrics(db)


@router.get("/queue", response_model=QueueStatusResponse)
def get_queue_status() -> QueueStatusResponse:
    return AdminService().get_queue_status()
