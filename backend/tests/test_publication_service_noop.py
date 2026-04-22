from types import SimpleNamespace

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
        external_comment_id='comment-1',
        published_body_markdown='same body',
        status='success',
    )
    session = SimpleNamespace(id='session-1', current_publication_id=None)
    db = FakeDB(latest)

    result = PublicationService().publish_or_update(
        db,
        session=session,
        review_run_id='run-1',
        body_markdown='same body',
        target_system='manual',
        target_object_id='manual-target',
    )

    assert result.publication_mode == 'noop'
    assert result.external_comment_id == 'comment-1'
    assert result.status == 'success'
