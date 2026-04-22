from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.finding_merge_service import FindingMergeService


class FakeQuery:
    def __init__(self, findings):
        self.findings = findings

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.findings


class FakeDB:
    def __init__(self, findings):
        self.findings = findings
        self.added = []

    def query(self, model):
        return FakeQuery(self.findings)

    def add(self, item):
        self.added.append(item)

    def flush(self):
        return None


def test_finding_merge_resolves_open_finding_when_not_returned_again() -> None:
    finding = SimpleNamespace(
        review_session_id='session-1',
        finding_key='gap:1',
        status='open',
        resolution_type=None,
        resolved_at=None,
        last_seen_run_id='run-old',
        title='Old',
        description='Old desc',
        category='requirement_gap',
        severity='medium',
        times_repeated=0,
        last_tone_level='strict',
    )
    db = FakeDB([finding])

    FindingMergeService().merge(
        db,
        session_id='session-1',
        review_run_id='run-new',
        llm_result={
            'resolved_finding_keys': [],
            'still_open_findings': [],
            'new_findings': [],
        },
    )

    assert finding.status == 'resolved'
    assert finding.resolution_type == 'fixed_in_source'
    assert finding.last_seen_run_id == 'run-new'
