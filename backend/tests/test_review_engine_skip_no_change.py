from types import SimpleNamespace

from app.services.review_engine import ReviewEngine


class FakeDB:
    def __init__(self):
        self.items = []

    def get(self, model, obj_id):
        return None

    def add(self, item):
        self.items.append(item)

    def flush(self):
        return None


class FakePublicationService:
    def __init__(self, publication=None):
        self.publication = publication
        self.calls = []

    def ensure_current_publication(
        self,
        db,
        *,
        session,
        review_run_id,
        target_system,
        target_object_id,
    ):
        self.calls.append(
            {
                "session": session,
                "review_run_id": review_run_id,
                "target_system": target_system,
                "target_object_id": target_object_id,
            }
        )
        return self.publication


def make_session():
    return SimpleNamespace(
        id="session-1",
        status="active",
        iteration_count=1,
        max_iterations=3,
        last_snapshot_id=None,
        last_review_run_id=None,
        last_seen_input_hash="hash-1",
        last_success_at=None,
        last_error_at=None,
        last_error_message=None,
        current_publication_id=None,
        findings=[],
        source_object=SimpleNamespace(
            source_type="jira_issue",
            external_system="jira",
            external_id="TEST-1",
        ),
    )


def test_review_engine_skips_when_input_hash_did_not_change() -> None:
    session = make_session()
    snapshot = SimpleNamespace(id="snapshot-1", normalized_text="same", content_hash="hash-1")
    db = FakeDB()
    publication_service = FakePublicationService()
    engine = ReviewEngine()
    engine.publication_service = publication_service

    result = engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert result.status == "skipped"
    assert session.last_seen_input_hash == "hash-1"
    assert publication_service.calls[0]["target_system"] == "jira"
    assert publication_service.calls[0]["target_object_id"] == "TEST-1"


def test_review_engine_marks_no_change_run_success_when_comment_was_recreated() -> None:
    session = make_session()
    snapshot = SimpleNamespace(id="snapshot-1", normalized_text="same", content_hash="hash-1")
    db = FakeDB()
    publication = SimpleNamespace(
        id="publication-1",
        status="success",
        publication_mode="create",
    )
    publication_service = FakePublicationService(publication=publication)
    engine = ReviewEngine()
    engine.publication_service = publication_service

    result = engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert result.status == "success"
    assert session.current_publication_id == "publication-1"


class FakeFailingLLMService:
    def review(self, prompt_payload):
        raise RuntimeError("LLM review failed after 1 attempt(s): HTTP 504 Gateway Time-out")


class FakePromptBuilder:
    def build_review_payload(self, **kwargs):
        return {
            "iteration_count": kwargs["iteration_count"],
            "max_iterations": kwargs["max_iterations"],
        }


def test_review_engine_failed_llm_run_does_not_advance_successful_snapshot_state() -> None:
    session = make_session()
    session.last_seen_input_hash = "old-hash"
    session.last_snapshot_id = "old-snapshot"
    snapshot = SimpleNamespace(id="new-snapshot", normalized_text="changed", content_hash="new-hash")
    db = FakeDB()
    engine = ReviewEngine()
    engine.llm_service = FakeFailingLLMService()
    engine.prompt_builder = FakePromptBuilder()

    try:
        engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")
    except RuntimeError as exc:
        assert "HTTP 504" in str(exc)
    else:
        raise AssertionError("Expected review run to fail")

    assert session.last_seen_input_hash == "old-hash"
    assert session.last_snapshot_id == "old-snapshot"
    assert session.last_success_at is None
    assert session.last_error_at is not None
    assert "HTTP 504" in session.last_error_message
