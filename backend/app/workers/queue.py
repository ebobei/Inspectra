from rq import Queue
from rq.job import Job
from redis import Redis

from app.config import settings

redis_conn = Redis.from_url(settings.redis_url)
default_queue = Queue("inspectra", connection=redis_conn)


def get_queue_counts() -> dict[str, int]:
    failed_registry = default_queue.failed_job_registry
    return {
        "queued": len(default_queue),
        "started": default_queue.started_job_registry.count,
        "failed": failed_registry.count,
        "deferred": default_queue.deferred_job_registry.count,
        "scheduled": default_queue.scheduled_job_registry.count,
    }


def enqueue_unique_recheck(*, session_id: str, trigger_type: str, event_fingerprint: str) -> tuple[bool, str]:
    from app.workers.jobs import sync_and_review_job

    job_id = f"recheck:{session_id}:{event_fingerprint}"
    existing = Job.fetch(job_id, connection=redis_conn, serializer=default_queue.serializer) if False else None
    try:
        existing = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        existing = None

    if existing is not None and existing.get_status(refresh=False) in {"queued", "started", "deferred", "scheduled"}:
        return False, job_id

    default_queue.enqueue(
        sync_and_review_job,
        session_id,
        trigger_type=trigger_type,
        job_id=job_id,
        job_timeout=900,
        result_ttl=3600,
        failure_ttl=86400,
    )
    return True, job_id
