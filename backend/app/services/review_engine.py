import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.review_run import ReviewRun
from app.models.review_session import ReviewSession
from app.models.source_snapshot import SourceSnapshot
from app.services.diff_service import DiffService
from app.services.finding_merge_service import FindingMergeService
from app.services.llm_service import LLMService
from app.services.prompt_builder import PromptBuilder
from app.services.publication_service import PublicationService
from app.services.tone_policy_service import TonePolicyService
from app.utils.hashing import sha256_text

logger = logging.getLogger(__name__)


class ReviewEngine:
    def __init__(self) -> None:
        self.llm_service = LLMService()
        self.prompt_builder = PromptBuilder()
        self.finding_merge_service = FindingMergeService()
        self.publication_service = PublicationService()
        self.tone_policy_service = TonePolicyService()
        self.diff_service = DiffService()

    def run_for_snapshot(
        self,
        db: Session,
        *,
        session: ReviewSession,
        snapshot: SourceSnapshot,
        trigger_type: str = "manual",
    ) -> ReviewRun:
        if session.status != "active":
            raise ValueError("Session is not active")

        previous_snapshot = None
        if session.last_snapshot_id and session.last_snapshot_id != snapshot.id:
            previous_snapshot = db.get(SourceSnapshot, session.last_snapshot_id)

        previous_text = previous_snapshot.normalized_text if previous_snapshot else None
        diff_result = self.diff_service.compare(previous_text, snapshot.normalized_text)

        if session.last_seen_input_hash == snapshot.content_hash or not diff_result.changed:
            return self._handle_no_change(
                db,
                session=session,
                snapshot=snapshot,
                trigger_type=trigger_type,
            )

        if session.iteration_count >= session.max_iterations:
            return self._publish_summary_only(
                db,
                session=session,
                snapshot=snapshot,
                trigger_type=trigger_type,
            )

        review_run = ReviewRun(
            review_session_id=session.id,
            snapshot_id=snapshot.id,
            run_type="initial" if session.iteration_count == 0 else "recheck",
            status="running",
            trigger_type=trigger_type,
            llm_model="configured-at-runtime",
            prompt_version="v2",
            input_hash=snapshot.content_hash,
            started_at=datetime.now(timezone.utc),
        )
        db.add(review_run)
        db.flush()

        try:
            open_findings = [
                {
                    "finding_key": finding.finding_key,
                    "category": finding.category,
                    "severity": finding.severity,
                    "title": finding.title,
                    "description": finding.description,
                    "status": finding.status,
                    "times_repeated": finding.times_repeated,
                    "tone_level": finding.last_tone_level,
                }
                for finding in session.findings
                if finding.status == "open"
            ]

            tone_level = self.tone_policy_service.get_tone_level(session.iteration_count + 1)
            prompt_payload = self.prompt_builder.build_review_payload(
                source_type=session.source_object.source_type,
                previous_text=previous_text,
                current_text=snapshot.normalized_text,
                open_findings=open_findings,
                tone_level=tone_level,
                iteration_count=session.iteration_count + 1,
                max_iterations=session.max_iterations,
            )
            prompt_payload["session_id"] = str(session.id)

            llm_result = self.llm_service.review(prompt_payload)
            review_run.output_hash = sha256_text(str(llm_result))

            self.finding_merge_service.merge(
                db,
                session_id=session.id,
                review_run_id=review_run.id,
                llm_result=llm_result,
            )

            publication = self.publication_service.publish_or_update(
                db,
                session=session,
                review_run_id=review_run.id,
                body_markdown=llm_result["final_comment_markdown"],
                target_system=session.source_object.external_system,
                target_object_id=session.source_object.external_id,
            )
            if publication.status == "failed":
                raise RuntimeError(publication.error_message or "Publication failed")

            review_run.status = "success"
            review_run.finished_at = datetime.now(timezone.utc)
            session.iteration_count += 1
            session.last_snapshot_id = snapshot.id
            session.last_review_run_id = review_run.id
            session.last_seen_input_hash = snapshot.content_hash
            session.last_success_at = datetime.now(timezone.utc)
            session.current_publication_id = publication.id
            session.last_error_at = None
            session.last_error_message = None
            db.flush()
            return review_run
        except Exception as exc:
            logger.error(
                "Review run failed",
                extra={"event_type": "review.run.failed", "session_id": session.id, "run_id": review_run.id},
                exc_info=True,
            )
            review_run.status = "failed"
            review_run.error_message = str(exc)
            review_run.finished_at = datetime.now(timezone.utc)
            session.last_error_at = datetime.now(timezone.utc)
            session.last_error_message = str(exc)
            db.flush()
            raise

    def _handle_no_change(
        self,
        db: Session,
        *,
        session: ReviewSession,
        snapshot: SourceSnapshot,
        trigger_type: str,
    ) -> ReviewRun:
        review_run = ReviewRun(
            review_session_id=session.id,
            snapshot_id=snapshot.id,
            run_type="recheck" if session.iteration_count > 0 else "initial",
            status="running",
            trigger_type=trigger_type,
            llm_model="not-called",
            prompt_version="skip-no-change",
            input_hash=snapshot.content_hash,
            output_hash=sha256_text("skip-no-change"),
            started_at=datetime.now(timezone.utc),
        )
        db.add(review_run)
        db.flush()

        try:
            publication = self.publication_service.ensure_current_publication(
                db,
                session=session,
                review_run_id=review_run.id,
                target_system=session.source_object.external_system,
                target_object_id=session.source_object.external_id,
            )
            if publication and publication.status == "failed":
                raise RuntimeError(publication.error_message or "Publication check failed")

            if publication and publication.publication_mode == "create":
                review_run.status = "success"
                review_run.output_hash = sha256_text("skip-no-change-comment-recreated")
            else:
                review_run.status = "skipped"
                review_run.output_hash = sha256_text("skip-no-change")

            review_run.finished_at = datetime.now(timezone.utc)
            session.last_snapshot_id = snapshot.id
            session.last_review_run_id = review_run.id
            session.last_seen_input_hash = snapshot.content_hash
            session.last_success_at = datetime.now(timezone.utc)
            if publication:
                session.current_publication_id = publication.id
            session.last_error_at = None
            session.last_error_message = None
            db.flush()
            return review_run
        except Exception as exc:
            logger.error(
                "No-change review run failed during publication check",
                extra={
                    "event_type": "review.no_change_publication_check.failed",
                    "session_id": str(session.id),
                    "run_id": str(review_run.id),
                },
                exc_info=True,
            )
            review_run.status = "failed"
            review_run.error_message = str(exc)
            review_run.finished_at = datetime.now(timezone.utc)
            session.last_error_at = datetime.now(timezone.utc)
            session.last_error_message = str(exc)
            db.flush()
            raise

    def _publish_summary_only(
        self,
        db: Session,
        *,
        session: ReviewSession,
        snapshot: SourceSnapshot,
        trigger_type: str,
    ) -> ReviewRun:
        review_run = ReviewRun(
            review_session_id=session.id,
            snapshot_id=snapshot.id,
            run_type="recheck",
            status="running",
            trigger_type=trigger_type,
            llm_model="not-called",
            prompt_version="summary-only",
            input_hash=snapshot.content_hash,
            output_hash=sha256_text("summary-only"),
            started_at=datetime.now(timezone.utc),
        )
        db.add(review_run)
        db.flush()

        try:
            open_findings = [finding for finding in session.findings if finding.status == "open"]
            body_lines = [
                "## Inspectra Review Summary",
                "",
                f"Review cycle limit reached ({session.max_iterations}).",
                "",
            ]
            if open_findings:
                body_lines.append("Remaining open findings:")
                for finding in open_findings:
                    body_lines.append(f"- [{finding.severity}] {finding.title}")
            else:
                body_lines.append("No open findings remain.")

            publication = self.publication_service.publish_or_update(
                db,
                session=session,
                review_run_id=review_run.id,
                body_markdown="\n".join(body_lines).strip() + "\n",
                target_system=session.source_object.external_system,
                target_object_id=session.source_object.external_id,
            )
            if publication.status == "failed":
                raise RuntimeError(publication.error_message or "Publication failed")

            review_run.status = "success"
            review_run.finished_at = datetime.now(timezone.utc)
            session.last_snapshot_id = snapshot.id
            session.last_review_run_id = review_run.id
            session.last_seen_input_hash = snapshot.content_hash
            session.last_success_at = datetime.now(timezone.utc)
            session.current_publication_id = publication.id
            session.last_error_at = None
            session.last_error_message = None
            db.flush()
            return review_run
        except Exception as exc:
            review_run.status = "failed"
            review_run.error_message = str(exc)
            review_run.finished_at = datetime.now(timezone.utc)
            session.last_error_at = datetime.now(timezone.utc)
            session.last_error_message = str(exc)
            db.flush()
            raise
