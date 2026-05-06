from types import SimpleNamespace

from app.connectors.jira_client import JiraCommentNotFoundError
from app.services.publication_service import PublicationService


class FakeQuery:
    def __init__(self, latest):
        self.latest = latest

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.latest


class FakeDB:
    def __init__(self, latest):
        self.latest = latest
        self.added = []

    def query(self, model):
        return FakeQuery(self.latest)

    def add(self, item):
        self.added.append(item)

    def flush(self):
        return None


def test_publication_service_returns_noop_when_body_is_unchanged() -> None:
    latest = SimpleNamespace(
        external_comment_id="comment-1",
        published_body_markdown="same body",
        status="success",
    )
    session = SimpleNamespace(id="session-1", current_publication_id=None)
    db = FakeDB(latest)

    result = PublicationService().publish_or_update(
        db,
        session=session,
        review_run_id="run-1",
        body_markdown="same body",
        target_system="manual",
        target_object_id="manual-target",
    )

    assert result.publication_mode == "noop"
    assert result.external_comment_id == "comment-1"
    assert result.status == "success"


def test_publication_service_checks_existing_comment_on_no_change() -> None:
    latest = SimpleNamespace(
        external_comment_id="comment-1",
        published_body_markdown="same body",
        status="success",
    )
    session = SimpleNamespace(id="session-1", current_publication_id=None)
    db = FakeDB(latest)
    service = PublicationService()
    calls = []

    def fake_ensure_external_comment_exists(**kwargs):
        calls.append(kwargs)

    service._ensure_external_comment_exists = fake_ensure_external_comment_exists

    result = service.ensure_current_publication(
        db,
        session=session,
        review_run_id="run-1",
        target_system="jira",
        target_object_id="TEST-1",
    )

    assert result.publication_mode == "noop"
    assert result.external_comment_id == "comment-1"
    assert result.status == "success"
    assert calls[0]["external_comment_id"] == "comment-1"


def test_publication_service_recreates_missing_comment_on_no_change() -> None:
    latest = SimpleNamespace(
        external_comment_id="comment-1",
        published_body_markdown="same body",
        status="success",
    )
    session = SimpleNamespace(id="session-1", current_publication_id=None)
    db = FakeDB(latest)
    service = PublicationService()

    def fake_ensure_external_comment_exists(**kwargs):
        raise JiraCommentNotFoundError("missing")

    def fake_publish_or_update(db_arg, **kwargs):
        assert db_arg is db
        assert kwargs["allow_noop"] is False
        assert kwargs["body_markdown"] == "same body"
        return SimpleNamespace(
            id="publication-2",
            publication_mode="create",
            external_comment_id="comment-2",
            status="success",
        )

    service._ensure_external_comment_exists = fake_ensure_external_comment_exists
    service.publish_or_update = fake_publish_or_update

    result = service.ensure_current_publication(
        db,
        session=session,
        review_run_id="run-1",
        target_system="jira",
        target_object_id="TEST-1",
    )

    assert result.publication_mode == "create"
    assert result.external_comment_id == "comment-2"
    assert result.status == "success"
