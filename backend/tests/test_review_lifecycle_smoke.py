from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.review_engine import ReviewEngine


class FakeDB:
    def __init__(self, objects=None):
        self.objects = objects or {}
        self.added = []
        self.flush_count = 0

    def add(self, item):
        self.added.append(item)
        if getattr(item, "id", None) is None:
            item.id = uuid4()

    def flush(self):
        self.flush_count += 1

    def get(self, model, obj_id):
        return self.objects.get(obj_id)


class FakePromptBuilder:
    def __init__(self):
        self.payloads = []

    def build_review_payload(self, **kwargs):
        self.payloads.append(kwargs)
        return dict(kwargs)


class FakeLLMService:
    def __init__(self, result=None, error=None):
        self.result = result or make_llm_result()
        self.error = error
        self.calls = []

    def review(self, prompt_payload):
        self.calls.append(prompt_payload)
        if self.error:
            raise self.error
        return self.result


class FakeFindingMergeService:
    def __init__(self):
        self.calls = []

    def merge(self, db, *, session_id, review_run_id, llm_result):
        self.calls.append(
            {
                "session_id": session_id,
                "review_run_id": review_run_id,
                "llm_result": llm_result,
            }
        )
        return []


class FakePublicationService:
    def __init__(self, publication=None):
        self.publication = publication or make_publication("publication-1", "success", "create")
        self.publish_calls = []
        self.ensure_calls = []

    def publish_or_update(self, db, *, session, review_run_id, body_markdown, target_system, target_object_id, allow_noop=True):
        self.publish_calls.append(
            {
                "session": session,
                "review_run_id": review_run_id,
                "body_markdown": body_markdown,
                "target_system": target_system,
                "target_object_id": target_object_id,
                "allow_noop": allow_noop,
            }
        )
        return self.publication

    def ensure_current_publication(self, db, *, session, review_run_id, target_system, target_object_id):
        self.ensure_calls.append(
            {
                "session": session,
                "review_run_id": review_run_id,
                "target_system": target_system,
                "target_object_id": target_object_id,
            }
        )
        return self.publication


class FakeTonePolicyService:
    def get_tone_level(self, iteration_number):
        return "neutral"


def make_llm_result(body="## AI Review\n\nNo blockers found."):
    return {
        "summary": "review completed",
        "resolved_finding_keys": [],
        "still_open_findings": [],
        "new_findings": [],
        "final_comment_markdown": body,
    }


def make_publication(publication_id="publication-1", status="success", mode="update"):
    return SimpleNamespace(
        id=publication_id,
        status=status,
        publication_mode=mode,
        external_comment_id="comment-1",
        error_message=None,
    )


def make_session(**overrides):
    data = {
        "id": "session-1",
        "status": "active",
        "iteration_count": 0,
        "max_iterations": 3,
        "last_snapshot_id": None,
        "last_review_run_id": None,
        "last_seen_input_hash": None,
        "last_success_at": None,
        "last_error_at": None,
        "last_error_message": None,
        "current_publication_id": None,
        "findings": [],
        "source_object": SimpleNamespace(
            source_type="jira_issue",
            external_system="jira",
            external_id="TEST-1",
        ),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_snapshot(snapshot_id="snapshot-1", text="current text", content_hash="hash-current"):
    return SimpleNamespace(
        id=snapshot_id,
        normalized_text=text,
        content_hash=content_hash,
    )


def make_engine(*, llm=None, publication=None, prompt_builder=None, finding_merge=None):
    engine = ReviewEngine()
    engine.llm_service = llm or FakeLLMService()
    engine.publication_service = publication or FakePublicationService()
    engine.prompt_builder = prompt_builder or FakePromptBuilder()
    engine.finding_merge_service = finding_merge or FakeFindingMergeService()
    engine.tone_policy_service = FakeTonePolicyService()
    return engine


def test_lifecycle_smoke_first_review_creates_managed_comment_and_success_state() -> None:
    session = make_session()
    snapshot = make_snapshot()
    db = FakeDB()
    llm = FakeLLMService()
    publication = FakePublicationService(make_publication("publication-1", "success", "create"))
    finding_merge = FakeFindingMergeService()
    engine = make_engine(llm=llm, publication=publication, finding_merge=finding_merge)

    result = engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert result.status == "success"
    assert result.run_type == "initial"
    assert len(llm.calls) == 1
    assert publication.publish_calls[0]["body_markdown"] == "## AI Review\n\nNo blockers found."
    assert publication.publish_calls[0]["target_system"] == "jira"
    assert publication.publish_calls[0]["target_object_id"] == "TEST-1"
    assert len(finding_merge.calls) == 1
    assert session.iteration_count == 1
    assert session.last_snapshot_id == "snapshot-1"
    assert session.last_seen_input_hash == "hash-current"
    assert session.current_publication_id == "publication-1"
    assert session.last_success_at is not None
    assert session.last_error_at is None
    assert session.last_error_message is None


def test_lifecycle_smoke_recheck_passes_previous_snapshot_and_open_findings_to_llm() -> None:
    previous_snapshot = make_snapshot("snapshot-old", "old text", "hash-old")
    open_finding = SimpleNamespace(
        finding_key="requirements:missing-ac",
        category="requirements",
        severity="medium",
        title="Missing acceptance criteria",
        description="The issue does not explain how to verify the result.",
        status="open",
        times_repeated=1,
        last_tone_level="neutral",
    )
    resolved_finding = SimpleNamespace(
        finding_key="requirements:resolved",
        category="requirements",
        severity="low",
        title="Already resolved",
        description="This should not be sent as open context.",
        status="resolved",
        times_repeated=0,
        last_tone_level="neutral",
    )
    session = make_session(
        iteration_count=1,
        last_snapshot_id="snapshot-old",
        last_seen_input_hash="hash-old",
        findings=[open_finding, resolved_finding],
    )
    snapshot = make_snapshot("snapshot-new", "new text", "hash-new")
    prompt_builder = FakePromptBuilder()
    llm = FakeLLMService()
    engine = make_engine(llm=llm, prompt_builder=prompt_builder)
    db = FakeDB(objects={"snapshot-old": previous_snapshot})

    result = engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert result.status == "success"
    assert result.run_type == "recheck"
    payload = prompt_builder.payloads[0]
    assert payload["previous_text"] == "old text"
    assert payload["current_text"] == "new text"
    assert payload["iteration_count"] == 2
    assert payload["max_iterations"] == 3
    assert payload["open_findings"] == [
        {
            "finding_key": "requirements:missing-ac",
            "category": "requirements",
            "severity": "medium",
            "title": "Missing acceptance criteria",
            "description": "The issue does not explain how to verify the result.",
            "status": "open",
            "times_repeated": 1,
            "tone_level": "neutral",
        }
    ]


def test_lifecycle_smoke_no_change_skips_llm_and_does_not_duplicate_comment() -> None:
    session = make_session(
        iteration_count=1,
        last_snapshot_id="snapshot-1",
        last_seen_input_hash="hash-current",
        current_publication_id="publication-1",
    )
    snapshot = make_snapshot("snapshot-1", "current text", "hash-current")
    llm = FakeLLMService(error=AssertionError("LLM must not be called for no-change run"))
    publication = FakePublicationService(make_publication("publication-2", "success", "noop"))
    engine = make_engine(llm=llm, publication=publication)
    db = FakeDB()

    result = engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert result.status == "skipped"
    assert len(llm.calls) == 0
    assert publication.publish_calls == []
    assert len(publication.ensure_calls) == 1
    assert session.current_publication_id == "publication-2"
    assert session.last_seen_input_hash == "hash-current"


def test_lifecycle_smoke_no_change_recreated_comment_finishes_successfully() -> None:
    session = make_session(
        iteration_count=1,
        last_snapshot_id="snapshot-1",
        last_seen_input_hash="hash-current",
        current_publication_id="publication-1",
    )
    snapshot = make_snapshot("snapshot-1", "current text", "hash-current")
    publication = FakePublicationService(make_publication("publication-2", "success", "create"))
    engine = make_engine(publication=publication)
    db = FakeDB()

    result = engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert result.status == "success"
    assert publication.ensure_calls[0]["target_system"] == "jira"
    assert publication.ensure_calls[0]["target_object_id"] == "TEST-1"
    assert session.current_publication_id == "publication-2"


def test_lifecycle_smoke_failed_llm_does_not_publish_or_advance_success_state() -> None:
    session = make_session(
        iteration_count=1,
        last_snapshot_id="snapshot-old",
        last_seen_input_hash="hash-old",
        last_success_at="previous-success",
        current_publication_id="publication-1",
    )
    snapshot = make_snapshot("snapshot-new", "changed text", "hash-new")
    llm = FakeLLMService(error=RuntimeError("LLM review failed after 1 attempt(s): HTTP 504 Gateway Time-out"))
    publication = FakePublicationService()
    engine = make_engine(llm=llm, publication=publication)
    db = FakeDB(objects={"snapshot-old": make_snapshot("snapshot-old", "old text", "hash-old")})

    with pytest.raises(RuntimeError, match="HTTP 504"):
        engine.run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type="manual")

    assert len(llm.calls) == 1
    assert publication.publish_calls == []
    assert publication.ensure_calls == []
    assert session.iteration_count == 1
    assert session.last_snapshot_id == "snapshot-old"
    assert session.last_seen_input_hash == "hash-old"
    assert session.last_success_at == "previous-success"
    assert session.current_publication_id == "publication-1"
    assert session.last_error_at is not None
    assert "HTTP 504" in session.last_error_message
