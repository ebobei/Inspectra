from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.connector_credential import ConnectorCredential
from app.models.review_session import ReviewSession
from app.schemas.reviews import ReviewRunResponse
from app.schemas.sessions import (
    FindingSummary,
    PublicationSummary,
    ReviewRunSummary,
    SessionCreateRequest,
    SessionDetailsResponse,
    SessionResponse,
    SessionRunRequest,
)
from app.services.audit_service import AuditService
from app.services.review_engine import ReviewEngine
from app.services.session_service import SessionService
from app.services.source_sync_service import SourceSyncService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
def list_sessions(db: Session = Depends(get_db)) -> list[ReviewSession]:
    return db.query(ReviewSession).order_by(ReviewSession.updated_at.desc()).all()


@router.post("", response_model=SessionResponse)
def create_session(payload: SessionCreateRequest, db: Session = Depends(get_db)) -> ReviewSession:
    external_system_map = {
        "jira_issue": "jira",
        "gitlab_merge_request": "gitlab",
        "confluence_page": "confluence",
        "manual_text": "manual",
    }
    external_system = external_system_map.get(payload.source_type)
    if not external_system:
        raise HTTPException(status_code=400, detail="Unsupported source_type")

    connector_credential_id = payload.connector_id
    if external_system == "manual":
        connector_credential_id = None
    else:
        if connector_credential_id is None:
            raise HTTPException(status_code=400, detail="connector_id is required for external sources")

        connector = db.get(ConnectorCredential, connector_credential_id)
        if connector is None:
            raise HTTPException(status_code=404, detail="Connector not found")
        if not connector.is_active:
            raise HTTPException(status_code=400, detail="Connector is inactive")
        if connector.connector_type != external_system:
            raise HTTPException(status_code=400, detail="Connector type does not match source_type")

    try:
        session = SessionService().create_session(
            db,
            source_type=payload.source_type,
            external_system=external_system,
            external_id=payload.external_id,
            title=payload.title,
            external_url=payload.external_url,
            connector_credential_id=connector_credential_id,
            max_iterations=payload.max_iterations,
            recheck_enabled=payload.recheck_enabled,
        )
        AuditService().log(
            db,
            event_type='session.created',
            entity_type='review_session',
            entity_id=session.id,
            payload={
                'source_type': payload.source_type,
                'external_system': external_system,
                'external_id': payload.external_id,
                'connector_credential_id': str(connector_credential_id) if connector_credential_id else None,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Session for this external object already exists")

    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionDetailsResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db)) -> SessionDetailsResponse:
    session = (
        db.query(ReviewSession)
        .options(
            selectinload(ReviewSession.source_object),
            selectinload(ReviewSession.findings),
            selectinload(ReviewSession.runs),
            selectinload(ReviewSession.publications),
        )
        .filter(ReviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    open_findings_count = sum(1 for finding in session.findings if finding.status == "open")
    resolved_findings_count = sum(1 for finding in session.findings if finding.status == "resolved")

    runs = [
        ReviewRunSummary.model_validate(run)
        for run in sorted(session.runs, key=lambda item: item.created_at, reverse=True)
    ]
    findings = [
        FindingSummary.model_validate(finding)
        for finding in sorted(session.findings, key=lambda item: item.created_at, reverse=True)
    ]
    publications = [
        PublicationSummary.model_validate(publication)
        for publication in sorted(session.publications, key=lambda item: item.created_at, reverse=True)
    ]

    return SessionDetailsResponse(
        **SessionResponse.model_validate(session).model_dump(),
        source_type=session.source_object.source_type,
        external_system=session.source_object.external_system,
        external_id=session.source_object.external_id,
        external_url=session.source_object.external_url,
        title=session.source_object.title,
        connector_credential_id=session.source_object.connector_credential_id,
        current_publication_id=session.current_publication_id,
        last_review_run_id=session.last_review_run_id,
        open_findings_count=open_findings_count,
        resolved_findings_count=resolved_findings_count,
        runs=runs,
        findings=findings,
        publications=publications,
    )


@router.post("/{session_id}/run", response_model=ReviewRunResponse)
def run_session(session_id: UUID, payload: SessionRunRequest, db: Session = Depends(get_db)) -> ReviewRunResponse:
    session = db.get(ReviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        snapshot = SourceSyncService().sync_session_source(db, session=session)
        review_run = ReviewEngine().run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type=payload.trigger_type)
        AuditService().log(
            db,
            event_type='session.run',
            entity_type='review_session',
            entity_id=session.id,
            payload={'trigger_type': payload.trigger_type, 'review_run_status': review_run.status},
        )
        db.commit()
    except Exception as exc:
        session = db.get(ReviewSession, session_id)
        if session is not None:
            session.last_error_message = str(exc)
            session.last_error_at = datetime.now(timezone.utc)
            db.commit()
        raise HTTPException(status_code=400, detail=str(exc))

    return ReviewRunResponse(session_id=session.id, status=review_run.status, queued=False)
