from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import settings
from app.services.security_service import SecurityService
from app.services.webhook_service import WebhookService


class FakeWebhookService(WebhookService):
    def __init__(self, *, queued=True, created=False):
        self.session = SimpleNamespace(id=uuid4())
        self.queued = queued
        self.created = created
        self.find_or_create_calls = []
        self.enqueue_calls = []

    def find_or_create_jira_session(self, db, *, issue_key, payload):
        self.find_or_create_calls.append(
            {
                "db": db,
                "issue_key": issue_key,
                "payload": payload,
            }
        )
        return self.session, self.created

    def enqueue_recheck(self, *, session_id, event_fingerprint):
        self.enqueue_calls.append(
            {
                "session_id": session_id,
                "event_fingerprint": event_fingerprint,
            }
        )
        return self.queued, "job-1"


def make_jira_payload(*, issue_key="MSU1C-1465", project_key="MSU1C", labels=None):
    return {
        "webhookEvent": "jira:issue_updated",
        "issue_event_type_name": "issue_updated",
        "issue": {
            "key": issue_key,
            "fields": {
                "project": {"key": project_key},
                "labels": labels or [],
                "summary": "Webhook auto review",
                "updated": "2026-05-08T10:00:00.000+0000",
            },
        },
    }


def configure_jira_webhook_settings(monkeypatch, *, allowed="MSU1C", required="", excluded="no-ai-review"):
    monkeypatch.setattr(settings, "jira_webhook_allowed_projects", allowed)
    monkeypatch.setattr(settings, "jira_webhook_required_label", required)
    monkeypatch.setattr(settings, "jira_webhook_excluded_label", excluded)


def test_jira_webhook_accepts_allowed_issue_and_queues_run(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch)
    service = FakeWebhookService(queued=True)

    result = service.handle_jira_webhook(None, payload=make_jira_payload())

    assert result.accepted is True
    assert result.queued is True
    assert result.external_id == "MSU1C-1465"
    assert result.session_id == service.session.id
    assert result.job_id == "job-1"
    assert result.reason is None
    assert service.find_or_create_calls[0]["issue_key"] == "MSU1C-1465"
    assert service.enqueue_calls[0]["session_id"] == str(service.session.id)


def test_jira_webhook_ignores_issue_from_not_allowed_project(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch, allowed="MSU1C,NSI")
    service = FakeWebhookService()

    result = service.handle_jira_webhook(
        None,
        payload=make_jira_payload(issue_key="PORTAL-1", project_key="PORTAL"),
    )

    assert result.accepted is True
    assert result.queued is False
    assert result.external_id == "PORTAL-1"
    assert "project is not allowed" in result.reason
    assert service.find_or_create_calls == []
    assert service.enqueue_calls == []


def test_jira_webhook_ignores_issue_with_excluded_label(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch, excluded="no-ai-review")
    service = FakeWebhookService()

    result = service.handle_jira_webhook(
        None,
        payload=make_jira_payload(labels=["no-ai-review"]),
    )

    assert result.accepted is True
    assert result.queued is False
    assert result.external_id == "MSU1C-1465"
    assert "excluded label no-ai-review" in result.reason
    assert service.find_or_create_calls == []
    assert service.enqueue_calls == []


def test_jira_webhook_can_require_opt_in_label(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch, required="ai-review", excluded="")
    service = FakeWebhookService()

    result = service.handle_jira_webhook(
        None,
        payload=make_jira_payload(labels=["other-label"]),
    )

    assert result.accepted is True
    assert result.queued is False
    assert result.external_id == "MSU1C-1465"
    assert "required label ai-review is missing" in result.reason
    assert service.find_or_create_calls == []
    assert service.enqueue_calls == []


def test_jira_webhook_returns_duplicate_reason_when_run_is_already_active(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch)
    service = FakeWebhookService(queued=False)

    result = service.handle_jira_webhook(None, payload=make_jira_payload())

    assert result.accepted is True
    assert result.queued is False
    assert result.job_id == "job-1"
    assert result.reason == "Duplicate webhook event already queued or running"
    assert len(service.find_or_create_calls) == 1
    assert len(service.enqueue_calls) == 1


def test_jira_webhook_falls_back_to_project_key_from_issue_key(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch, allowed="MSU1C")
    service = FakeWebhookService()
    payload = make_jira_payload(project_key="")
    payload["issue"]["fields"].pop("project")

    result = service.handle_jira_webhook(None, payload=payload)

    assert result.accepted is True
    assert result.queued is True
    assert service.find_or_create_calls[0]["issue_key"] == "MSU1C-1465"


def test_jira_webhook_rejects_unsupported_payload(monkeypatch) -> None:
    configure_jira_webhook_settings(monkeypatch)
    service = FakeWebhookService()

    result = service.handle_jira_webhook(None, payload={"webhookEvent": "jira:issue_updated"})

    assert result.accepted is True
    assert result.queued is False
    assert result.reason == "Unsupported Jira webhook payload"
    assert service.find_or_create_calls == []
    assert service.enqueue_calls == []


def test_webhook_secret_accepts_header(monkeypatch) -> None:
    monkeypatch.setattr(settings, "webhook_shared_secret", "secret-1")
    request = SimpleNamespace(
        headers={"x-inspectra-webhook-secret": "secret-1"},
        query_params={},
    )

    SecurityService().verify_webhook_secret(request)


def test_webhook_secret_accepts_query_parameter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "webhook_shared_secret", "secret-1")
    request = SimpleNamespace(
        headers={},
        query_params={"secret": "secret-1"},
    )

    SecurityService().verify_webhook_secret(request)


def test_webhook_secret_rejects_invalid_value(monkeypatch) -> None:
    monkeypatch.setattr(settings, "webhook_shared_secret", "secret-1")
    request = SimpleNamespace(
        headers={},
        query_params={"secret": "wrong"},
    )

    with pytest.raises(HTTPException) as exc_info:
        SecurityService().verify_webhook_secret(request)

    assert exc_info.value.status_code == 401
