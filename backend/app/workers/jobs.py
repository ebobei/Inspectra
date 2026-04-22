import logging
from datetime import datetime, timezone

from app.db import SessionLocal
from app.models.review_session import ReviewSession
from app.models.source_snapshot import SourceSnapshot
from app.services.review_engine import ReviewEngine
from app.services.source_sync_service import SourceSyncService

logger = logging.getLogger(__name__)


def run_review_job(session_id: str, snapshot_id: str, trigger_type: str = "manual") -> None:
    db = SessionLocal()
    try:
        session = db.get(ReviewSession, session_id)
        snapshot = db.get(SourceSnapshot, snapshot_id)
        if session is None or snapshot is None:
            raise ValueError("Session or snapshot not found")

        ReviewEngine().run_for_snapshot(
            db,
            session=session,
            snapshot=snapshot,
            trigger_type=trigger_type,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        session = db.get(ReviewSession, session_id)
        if session is not None:
            session.last_error_at = datetime.now(timezone.utc)
            session.last_error_message = str(exc)
            db.commit()
        logger.error("run_review_job failed", extra={"event_type": "worker.run_review.failed", "session_id": session_id}, exc_info=True)
        raise
    finally:
        db.close()



def sync_and_review_job(session_id: str, trigger_type: str = "webhook") -> None:
    db = SessionLocal()
    try:
        session = db.get(ReviewSession, session_id)
        if session is None:
            raise ValueError("Session not found")
        if session.status != "active":
            return
        if not session.recheck_enabled:
            return

        snapshot = SourceSyncService().sync_session_source(db, session=session)
        ReviewEngine().run_for_snapshot(
            db,
            session=session,
            snapshot=snapshot,
            trigger_type=trigger_type,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        session = db.get(ReviewSession, session_id)
        if session is not None:
            session.last_error_at = datetime.now(timezone.utc)
            session.last_error_message = str(exc)
            db.commit()
        logger.error("sync_and_review_job failed", extra={"event_type": "worker.sync_review.failed", "session_id": session_id}, exc_info=True)
        raise
    finally:
        db.close()
