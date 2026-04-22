from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.publication import Publication
from app.models.review_session import ReviewSession
from app.workers.queue import get_queue_counts


class AdminService:
    def get_metrics(self, db: Session) -> dict:
        active_sessions = db.query(func.count(ReviewSession.id)).filter(ReviewSession.status == "active").scalar() or 0
        paused_sessions = db.query(func.count(ReviewSession.id)).filter(ReviewSession.status == "paused").scalar() or 0
        error_sessions = db.query(func.count(ReviewSession.id)).filter(ReviewSession.status == "error").scalar() or 0
        successful_publications = db.query(func.count(Publication.id)).filter(Publication.status == "success").scalar() or 0
        failed_publications = db.query(func.count(Publication.id)).filter(Publication.status == "failed").scalar() or 0
        queue_counts = get_queue_counts()
        return {
            "active_sessions": active_sessions,
            "paused_sessions": paused_sessions,
            "error_sessions": error_sessions,
            "successful_publications": successful_publications,
            "failed_publications": failed_publications,
            "queued_jobs": queue_counts["queued"],
            "started_jobs": queue_counts["started"],
            "failed_jobs": queue_counts["failed"],
        }

    def get_queue_status(self) -> dict:
        return get_queue_counts()
