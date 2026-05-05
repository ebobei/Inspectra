import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.confluence_client import (
    ConfluenceClient,
    ConfluenceCommentNotFoundError,
)
from app.connectors.gitlab_client import GitLabClient, GitLabNoteNotFoundError
from app.connectors.jira_client import JiraClient, JiraCommentNotFoundError
from app.models.connector_credential import ConnectorCredential
from app.models.publication import Publication
from app.models.review_session import ReviewSession
from app.services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


class PublicationService:
    def publish_or_update(
        self,
        db: Session,
        *,
        session: ReviewSession,
        review_run_id,
        body_markdown: str,
        target_system: str,
        target_object_id: str,
    ) -> Publication:
        latest = (
            db.query(Publication)
            .filter(Publication.review_session_id == session.id)
            .order_by(Publication.created_at.desc())
            .first()
        )

        external_comment_id = latest.external_comment_id if latest else None

        if (
            latest
            and latest.published_body_markdown == body_markdown
            and latest.status == "success"
        ):
            publication = Publication(
                review_session_id=session.id,
                review_run_id=review_run_id,
                target_system=target_system,
                target_object_id=target_object_id,
                external_comment_id=external_comment_id,
                published_body_markdown=body_markdown,
                publication_mode="noop",
                status="success",
                published_at=datetime.now(timezone.utc),
                error_message=None,
            )
            db.add(publication)
            db.flush()
            session.current_publication_id = publication.id
            return publication

        status = "success"
        error_message = None
        publication_mode = "update" if external_comment_id else "create"

        try:
            (
                external_comment_id,
                publication_mode,
                fallback_message,
            ) = self._publish_with_retries(
                db=db,
                session=session,
                target_system=target_system,
                target_object_id=target_object_id,
                external_comment_id=external_comment_id,
                body_markdown=body_markdown,
            )
            error_message = fallback_message
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            logger.error(
                "Publication failed",
                extra={
                    "event_type": "publication.failed",
                    "session_id": str(session.id),
                    "run_id": str(review_run_id),
                    "target_system": target_system,
                    "target_object_id": target_object_id,
                },
                exc_info=True,
            )

        publication = Publication(
            review_session_id=session.id,
            review_run_id=review_run_id,
            target_system=target_system,
            target_object_id=target_object_id,
            external_comment_id=external_comment_id,
            published_body_markdown=body_markdown,
            publication_mode=publication_mode,
            status=status,
            published_at=datetime.now(timezone.utc) if status == "success" else None,
            error_message=error_message,
        )
        db.add(publication)
        db.flush()

        session.current_publication_id = publication.id
        return publication

    def _publish_with_retries(self, **kwargs) -> tuple[str, str, str | None]:
        last_error: Exception | None = None

        for attempt in range(1, settings.publish_max_retries + 1):
            try:
                return self._publish_once(**kwargs)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Publication attempt failed",
                    extra={
                        "event_type": "publication.retry",
                        "session_id": str(kwargs["session"].id),
                        "target_system": kwargs["target_system"],
                        "target_object_id": kwargs["target_object_id"],
                        "attempt": attempt,
                    },
                    exc_info=True,
                )
                if attempt < settings.publish_max_retries:
                    time.sleep(min(attempt, 3))

        assert last_error is not None
        raise last_error

    def _publish_once(
        self,
        db: Session,
        session: ReviewSession,
        target_system: str,
        target_object_id: str,
        external_comment_id: str | None,
        body_markdown: str,
    ) -> tuple[str, str, str | None]:
        if target_system == "jira":
            return self._publish_jira(
                db=db,
                session=session,
                issue_key=target_object_id,
                external_comment_id=external_comment_id,
                body_markdown=body_markdown,
            )

        if target_system == "gitlab":
            return self._publish_gitlab(
                db=db,
                session=session,
                target_object_id=target_object_id,
                external_comment_id=external_comment_id,
                body_markdown=body_markdown,
            )

        if target_system == "confluence":
            return self._publish_confluence(
                db=db,
                session=session,
                page_id=target_object_id,
                external_comment_id=external_comment_id,
                body_markdown=body_markdown,
            )

        if target_system == "manual":
            return (external_comment_id or "manual-comment", "create", None)

        raise ValueError(f"Unsupported target_system: {target_system}")

    def _get_credential(
        self,
        db: Session,
        *,
        session: ReviewSession,
        expected_type: str,
    ) -> ConnectorCredential:
        credential_id = session.source_object.connector_credential_id
        if credential_id is None:
            raise ValueError(
                f"{expected_type} source object is missing connector credential"
            )

        credential = db.get(ConnectorCredential, credential_id)
        if (
            credential is None
            or credential.connector_type != expected_type
            or not credential.is_active
        ):
            raise ValueError(f"Active {expected_type} connector credential not found")

        return credential

    def _publish_jira(
        self,
        db: Session,
        session: ReviewSession,
        issue_key: str,
        external_comment_id: str | None,
        body_markdown: str,
    ) -> tuple[str, str, str | None]:
        credential = self._get_credential(db, session=session, expected_type="jira")
        token = CryptoService().decrypt(credential.secret_encrypted)
        jira = JiraClient(
            base_url=credential.base_url,
            token=token,
            auth_type=credential.auth_type,
        )

        if external_comment_id:
            try:
                jira.update_comment(
                    issue_key=issue_key,
                    comment_id=external_comment_id,
                    body=body_markdown,
                )
                return external_comment_id, "update", None
            except JiraCommentNotFoundError:
                new_comment_id = jira.create_comment(
                    issue_key=issue_key,
                    body=body_markdown,
                )
                logger.warning(
                    "Jira comment not found during update; created a new comment",
                    extra={
                        "event_type": "publication.comment_recreated",
                        "session_id": str(session.id),
                        "target_system": "jira",
                        "target_object_id": issue_key,
                        "old_comment_id": external_comment_id,
                        "new_comment_id": new_comment_id,
                    },
                )
                return (
                    new_comment_id,
                    "create",
                    (
                        f"Previous external comment '{external_comment_id}' was not found. "
                        "Created a new comment instead."
                    ),
                )

        new_comment_id = jira.create_comment(issue_key=issue_key, body=body_markdown)
        return new_comment_id, "create", None

    def _publish_gitlab(
        self,
        db: Session,
        session: ReviewSession,
        target_object_id: str,
        external_comment_id: str | None,
        body_markdown: str,
    ) -> tuple[str, str, str | None]:
        credential = self._get_credential(db, session=session, expected_type="gitlab")
        token = CryptoService().decrypt(credential.secret_encrypted)
        gitlab = GitLabClient(base_url=credential.base_url, token=token)
        project_id, mr_iid = gitlab.parse_external_id(target_object_id)

        if external_comment_id:
            try:
                gitlab.update_note(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    note_id=external_comment_id,
                    body=body_markdown,
                )
                return external_comment_id, "update", None
            except GitLabNoteNotFoundError:
                new_comment_id = gitlab.create_note(
                    project_id=project_id,
                    mr_iid=mr_iid,
                    body=body_markdown,
                )
                logger.warning(
                    "GitLab note not found during update; created a new note",
                    extra={
                        "event_type": "publication.comment_recreated",
                        "session_id": str(session.id),
                        "target_system": "gitlab",
                        "target_object_id": target_object_id,
                        "old_comment_id": external_comment_id,
                        "new_comment_id": new_comment_id,
                    },
                )
                return (
                    new_comment_id,
                    "create",
                    (
                        f"Previous external comment '{external_comment_id}' was not found. "
                        "Created a new comment instead."
                    ),
                )

        new_comment_id = gitlab.create_note(
            project_id=project_id,
            mr_iid=mr_iid,
            body=body_markdown,
        )
        return new_comment_id, "create", None

    def _publish_confluence(
        self,
        db: Session,
        session: ReviewSession,
        page_id: str,
        external_comment_id: str | None,
        body_markdown: str,
    ) -> tuple[str, str, str | None]:
        credential = self._get_credential(
            db,
            session=session,
            expected_type="confluence",
        )
        token = CryptoService().decrypt(credential.secret_encrypted)
        confluence = ConfluenceClient(
            base_url=credential.base_url,
            token=token,
            auth_type=credential.auth_type,
        )

        if external_comment_id:
            try:
                confluence.update_comment(
                    page_id=page_id,
                    comment_id=external_comment_id,
                    body=body_markdown,
                )
                return external_comment_id, "update", None
            except ConfluenceCommentNotFoundError:
                new_comment_id = confluence.create_comment(
                    page_id=page_id,
                    body=body_markdown,
                )
                logger.warning(
                    "Confluence comment not found during update; created a new comment",
                    extra={
                        "event_type": "publication.comment_recreated",
                        "session_id": str(session.id),
                        "target_system": "confluence",
                        "target_object_id": page_id,
                        "old_comment_id": external_comment_id,
                        "new_comment_id": new_comment_id,
                    },
                )
                return (
                    new_comment_id,
                    "create",
                    (
                        f"Previous external comment '{external_comment_id}' was not found. "
                        "Created a new comment instead."
                    ),
                )

        new_comment_id = confluence.create_comment(page_id=page_id, body=body_markdown)
        return new_comment_id, "create", None