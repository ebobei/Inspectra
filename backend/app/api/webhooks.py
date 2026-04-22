import json
from hashlib import sha256
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.review_session import ReviewSession
from app.models.source_object import SourceObject
from app.schemas.webhooks import WebhookAcceptedResponse
from app.services.security_service import SecurityService
from app.workers.queue import enqueue_unique_recheck

router = APIRouter(prefix='/webhooks', tags=['webhooks'])
security_service = SecurityService()


def _jira_issue_key(payload: dict[str, Any]) -> str | None:
    issue = payload.get('issue') or {}
    key = issue.get('key')
    if isinstance(key, str) and key.strip():
        return key.strip()
    return None


def _jira_event_fingerprint(payload: dict[str, Any]) -> str:
    issue = payload.get('issue') or {}
    fields = issue.get('fields') or {}
    updated = fields.get('updated') or payload.get('timestamp') or payload.get('webhookEvent')
    source = {
        'webhookEvent': payload.get('webhookEvent'),
        'issue_event_type_name': payload.get('issue_event_type_name'),
        'issue_key': issue.get('key'),
        'updated': updated,
        'changelog_id': (payload.get('changelog') or {}).get('id'),
    }
    raw = json.dumps(source, sort_keys=True, ensure_ascii=False)
    return sha256(raw.encode('utf-8')).hexdigest()[:24]


def _gitlab_external_id(payload: dict[str, Any]) -> str | None:
    if payload.get('object_kind') != 'merge_request':
        return None
    attrs = payload.get('object_attributes') or {}
    project = payload.get('project') or {}
    project_id = project.get('id')
    mr_iid = attrs.get('iid')
    if project_id is None or mr_iid is None:
        return None
    return f'{project_id}!{mr_iid}'


def _gitlab_event_fingerprint(payload: dict[str, Any]) -> str:
    attrs = payload.get('object_attributes') or {}
    source = {
        'object_kind': payload.get('object_kind'),
        'project_id': (payload.get('project') or {}).get('id'),
        'iid': attrs.get('iid'),
        'updated_at': attrs.get('updated_at'),
        'last_commit': ((attrs.get('last_commit') or {}).get('id')),
    }
    raw = json.dumps(source, sort_keys=True, ensure_ascii=False)
    return sha256(raw.encode('utf-8')).hexdigest()[:24]


def _confluence_page_id(payload: dict[str, Any]) -> str | None:
    page = payload.get('page') or payload.get('content') or {}
    page_id = page.get('id')
    if page_id is None:
        return None
    return str(page_id)


def _confluence_event_fingerprint(payload: dict[str, Any]) -> str:
    page = payload.get('page') or payload.get('content') or {}
    version = (page.get('version') or {}).get('number') or payload.get('version')
    source = {
        'eventType': payload.get('eventType') or payload.get('webhookEvent'),
        'page_id': page.get('id'),
        'version': version,
    }
    raw = json.dumps(source, sort_keys=True, ensure_ascii=False)
    return sha256(raw.encode('utf-8')).hexdigest()[:24]


def _queue_for_external_id(db: Session, *, external_system: str, external_id: str, event_fingerprint: str) -> WebhookAcceptedResponse:
    session = (
        db.query(ReviewSession)
        .join(ReviewSession.source_object)
        .filter(
            ReviewSession.status == 'active',
            ReviewSession.recheck_enabled.is_(True),
            SourceObject.external_system == external_system,
            SourceObject.external_id == external_id,
        )
        .first()
    )
    if session is None:
        return WebhookAcceptedResponse(accepted=True, queued=False, reason=f'No active session for {external_system} object')

    queued, _job_id = enqueue_unique_recheck(
        session_id=str(session.id),
        trigger_type='webhook',
        event_fingerprint=event_fingerprint,
    )
    reason = None if queued else 'Duplicate webhook event already queued'
    return WebhookAcceptedResponse(accepted=True, queued=queued, session_id=session.id, reason=reason)


@router.post('/jira', response_model=WebhookAcceptedResponse)
async def jira_webhook(request: Request, db: Session = Depends(get_db)) -> WebhookAcceptedResponse:
    security_service.verify_webhook_secret(request)
    payload = await request.json()
    issue_key = _jira_issue_key(payload)
    if not issue_key:
        return WebhookAcceptedResponse(accepted=True, queued=False, reason='Unsupported Jira webhook payload')
    return _queue_for_external_id(db, external_system='jira', external_id=issue_key, event_fingerprint=_jira_event_fingerprint(payload))


@router.post('/gitlab', response_model=WebhookAcceptedResponse)
async def gitlab_webhook(request: Request, db: Session = Depends(get_db)) -> WebhookAcceptedResponse:
    security_service.verify_webhook_secret(request)
    payload = await request.json()
    external_id = _gitlab_external_id(payload)
    if not external_id:
        return WebhookAcceptedResponse(accepted=True, queued=False, reason='Unsupported GitLab webhook payload')
    return _queue_for_external_id(db, external_system='gitlab', external_id=external_id, event_fingerprint=_gitlab_event_fingerprint(payload))


@router.post('/confluence', response_model=WebhookAcceptedResponse)
async def confluence_webhook(request: Request, db: Session = Depends(get_db)) -> WebhookAcceptedResponse:
    security_service.verify_webhook_secret(request)
    payload = await request.json()
    page_id = _confluence_page_id(payload)
    if not page_id:
        return WebhookAcceptedResponse(accepted=True, queued=False, reason='Unsupported Confluence webhook payload')
    return _queue_for_external_id(db, external_system='confluence', external_id=page_id, event_fingerprint=_confluence_event_fingerprint(payload))
