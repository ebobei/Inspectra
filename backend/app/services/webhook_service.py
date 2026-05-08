import json
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models.connector_credential import ConnectorCredential
from app.models.review_session import ReviewSession
from app.models.source_object import SourceObject
from app.schemas.webhooks import WebhookAcceptedResponse
from app.services.session_service import SessionService
from app.workers.queue import enqueue_unique_recheck


class WebhookService:
    def handle_jira_webhook(self, db: Session, *, payload: dict[str, Any]) -> WebhookAcceptedResponse:
        issue_key = self.extract_jira_issue_key(payload)
        if not issue_key:
            return WebhookAcceptedResponse(
                accepted=True,
                queued=False,
                reason="Unsupported Jira webhook payload",
            )

        project_key = self.extract_jira_project_key(payload, issue_key=issue_key)
        labels = self.extract_jira_labels(payload)

        ignore_reason = self.get_jira_ignore_reason(
            issue_key=issue_key,
            project_key=project_key,
            labels=labels,
        )
        if ignore_reason:
            return WebhookAcceptedResponse(
                accepted=True,
                queued=False,
                external_id=issue_key,
                reason=ignore_reason,
            )

        session, created = self.find_or_create_jira_session(
            db,
            issue_key=issue_key,
            payload=payload,
        )
        if created:
            db.commit()
            db.refresh(session)

        queued, job_id = self.enqueue_recheck(
            session_id=str(session.id),
            event_fingerprint=self.jira_event_fingerprint(payload),
        )
        reason = None if queued else "Duplicate webhook event already queued or running"
        return WebhookAcceptedResponse(
            accepted=True,
            queued=queued,
            session_id=session.id,
            external_id=issue_key,
            job_id=job_id,
            reason=reason,
        )

    def enqueue_recheck(self, *, session_id: str, event_fingerprint: str) -> tuple[bool, str]:
        return enqueue_unique_recheck(
            session_id=session_id,
            trigger_type="webhook",
            event_fingerprint=event_fingerprint,
        )

    def extract_jira_issue_key(self, payload: dict[str, Any]) -> str | None:
        issue = payload.get("issue") or {}
        key = issue.get("key")
        if isinstance(key, str) and key.strip():
            return key.strip()
        return None

    def extract_jira_project_key(self, payload: dict[str, Any], *, issue_key: str) -> str | None:
        issue = payload.get("issue") or {}
        fields = issue.get("fields") or {}
        project = fields.get("project") or {}
        project_key = project.get("key")
        if isinstance(project_key, str) and project_key.strip():
            return project_key.strip().upper()

        if "-" in issue_key:
            return issue_key.split("-", 1)[0].strip().upper()
        return None

    def extract_jira_labels(self, payload: dict[str, Any]) -> set[str]:
        issue = payload.get("issue") or {}
        fields = issue.get("fields") or {}
        raw_labels = fields.get("labels") or []
        if not isinstance(raw_labels, list):
            return set()
        return {str(label).strip().lower() for label in raw_labels if str(label).strip()}

    def get_jira_ignore_reason(self, *, issue_key: str, project_key: str | None, labels: set[str]) -> str | None:
        allowed_projects = self._csv_to_set(settings.jira_webhook_allowed_projects, uppercase=True)
        if allowed_projects:
            if not project_key or project_key.upper() not in allowed_projects:
                return f"Ignored Jira issue {issue_key}: project is not allowed"

        excluded_label = self._optional_setting(settings.jira_webhook_excluded_label)
        if excluded_label and excluded_label.lower() in labels:
            return f"Ignored Jira issue {issue_key}: excluded label {excluded_label} is present"

        required_label = self._optional_setting(settings.jira_webhook_required_label)
        if required_label and required_label.lower() not in labels:
            return f"Ignored Jira issue {issue_key}: required label {required_label} is missing"

        return None

    def find_or_create_jira_session(
        self,
        db: Session,
        *,
        issue_key: str,
        payload: dict[str, Any],
    ) -> tuple[ReviewSession, bool]:
        existing = (
            db.query(ReviewSession)
            .join(ReviewSession.source_object)
            .filter(
                SourceObject.external_system == "jira",
                SourceObject.external_id == issue_key,
            )
            .first()
        )
        if existing is not None:
            if existing.status != "active":
                raise ValueError(f"Review session for Jira issue {issue_key} is not active")
            if not existing.recheck_enabled:
                raise ValueError(f"Review session for Jira issue {issue_key} has recheck disabled")
            return existing, False

        connector = self.get_jira_connector(db)
        issue = payload.get("issue") or {}
        fields = issue.get("fields") or {}
        title = fields.get("summary") if isinstance(fields.get("summary"), str) else issue_key
        external_url = f"{connector.base_url.rstrip('/')}/browse/{issue_key}"

        session = SessionService().create_session(
            db,
            source_type="jira_issue",
            external_system="jira",
            external_id=issue_key,
            title=title,
            external_url=external_url,
            connector_credential_id=connector.id,
            max_iterations=settings.default_max_iterations,
            recheck_enabled=settings.recheck_enabled_default,
        )
        return session, True

    def get_jira_connector(self, db: Session) -> ConnectorCredential:
        configured_connector_id = self._optional_setting(settings.jira_webhook_connector_id)
        if configured_connector_id:
            connector = db.get(ConnectorCredential, UUID(configured_connector_id))
            if connector is None or connector.connector_type != "jira" or not connector.is_active:
                raise ValueError("Configured Jira webhook connector is not found or inactive")
            return connector

        connectors = (
            db.query(ConnectorCredential)
            .filter(
                ConnectorCredential.connector_type == "jira",
                ConnectorCredential.is_active.is_(True),
            )
            .all()
        )
        if len(connectors) == 1:
            return connectors[0]
        if not connectors:
            raise ValueError("No active Jira connector credential found for webhook auto-session")
        raise ValueError("Multiple active Jira connectors found; set JIRA_WEBHOOK_CONNECTOR_ID")

    def jira_event_fingerprint(self, payload: dict[str, Any]) -> str:
        issue = payload.get("issue") or {}
        fields = issue.get("fields") or {}
        changelog = payload.get("changelog") or {}
        source = {
            "webhookEvent": payload.get("webhookEvent"),
            "issue_event_type_name": payload.get("issue_event_type_name"),
            "issue_key": issue.get("key"),
            "updated": fields.get("updated") or payload.get("timestamp"),
            "changelog_id": changelog.get("id"),
        }
        raw = json.dumps(source, sort_keys=True, ensure_ascii=False)
        return sha256(raw.encode("utf-8")).hexdigest()[:24]

    def _csv_to_set(self, value: str | None, *, uppercase: bool = False) -> set[str]:
        if not value:
            return set()
        result = set()
        for item in value.split(","):
            cleaned = item.strip()
            if not cleaned:
                continue
            result.add(cleaned.upper() if uppercase else cleaned)
        return result

    def _optional_setting(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
