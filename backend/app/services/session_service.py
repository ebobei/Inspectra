import uuid

from sqlalchemy.orm import Session

from app.models.review_session import ReviewSession
from app.models.source_object import SourceObject


class SessionService:
    def create_session(
        self,
        db: Session,
        *,
        source_type: str,
        external_system: str,
        external_id: str,
        title: str | None,
        external_url: str | None,
        connector_credential_id: uuid.UUID | None,
        max_iterations: int,
        recheck_enabled: bool,
    ) -> ReviewSession:
        source_object = SourceObject(
            source_type=source_type,
            external_system=external_system,
            external_id=external_id,
            title=title,
            external_url=external_url,
            connector_credential_id=connector_credential_id,
            is_active=True,
        )
        db.add(source_object)
        db.flush()

        session = ReviewSession(
            source_object_id=source_object.id,
            status="active",
            max_iterations=max_iterations,
            recheck_enabled=recheck_enabled,
        )
        db.add(session)
        db.flush()
        return session

    def get_session(self, db: Session, session_id) -> ReviewSession | None:
        return db.get(ReviewSession, session_id)
