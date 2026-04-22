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


def test_review_engine_skips_when_input_hash_did_not_change() -> None:
    session = SimpleNamespace(
        id='session-1',
        status='active',
        iteration_count=1,
        max_iterations=3,
        last_snapshot_id=None,
        last_review_run_id=None,
        last_seen_input_hash='hash-1',
        last_success_at=None,
        last_error_at=None,
        last_error_message=None,
        findings=[],
        source_object=SimpleNamespace(source_type='jira_issue'),
    )
    snapshot = SimpleNamespace(id='snapshot-1', normalized_text='same', content_hash='hash-1')
    db = FakeDB()

    result = ReviewEngine().run_for_snapshot(db, session=session, snapshot=snapshot, trigger_type='manual')

    assert result.status == 'skipped'
    assert session.last_seen_input_hash == 'hash-1'
