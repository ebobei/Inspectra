from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.reviews import ManualReviewRequest, ReviewRunResponse
from app.services.audit_service import AuditService
from app.services.review_engine import ReviewEngine
from app.services.session_service import SessionService
from app.services.source_sync_service import SourceSyncService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/manual", response_model=ReviewRunResponse)
def run_manual_review(payload: ManualReviewRequest, db: Session = Depends(get_db)) -> ReviewRunResponse:
    session_service = SessionService()
    source_sync_service = SourceSyncService()
    review_engine = ReviewEngine()

    session = session_service.create_session(
        db,
        source_type="manual_text",
        external_system="manual",
        external_id=f"manual-{uuid4()}",
        title=payload.title,
        external_url=None,
        connector_credential_id=None,
        max_iterations=payload.max_iterations,
        recheck_enabled=True,
    )

    snapshot = source_sync_service.create_manual_snapshot(
        db,
        source_object=session.source_object,
        text=payload.text,
        raw_payload={"title": payload.title, "text": payload.text},
        metadata={},
    )

    review_run = review_engine.run_for_snapshot(
        db,
        session=session,
        snapshot=snapshot,
        trigger_type="manual",
    )
    AuditService().log(
        db,
        event_type='manual_review.run',
        entity_type='review_session',
        entity_id=session.id,
        payload={'review_run_status': review_run.status},
    )

    db.commit()
    return ReviewRunResponse(session_id=session.id, status=review_run.status, queued=False)
