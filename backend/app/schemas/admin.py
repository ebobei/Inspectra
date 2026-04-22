from pydantic import BaseModel


class AdminMetricsResponse(BaseModel):
    active_sessions: int
    paused_sessions: int
    error_sessions: int
    successful_publications: int
    failed_publications: int
    queued_jobs: int
    started_jobs: int
    failed_jobs: int


class QueueStatusResponse(BaseModel):
    queued: int
    started: int
    failed: int
    deferred: int
    scheduled: int
