import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.confluence_client import ConfluenceClient
from app.connectors.gitlab_client import GitLabClient
from app.connectors.jira_client import JiraClient
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
        if latest and latest.published_body_markdown == body_markdown and latest.status == "success":
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

        publication_mode = "update" if external_comment_id else "create"
        status = "success"
        error_message = None

        try:
            external_comment_id = self._publish_with_retries(
                db=db,
                session=session,
                target_system=target_system,
                target_object_id=target_object_id,
                external_comment_id=external_comment_id,
                body_markdown=body_markdown,
            )
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            logger.error(
                "Publication failed",
                extra={"event_type": "publication.failed", "session_id": session.id, "run_id": review_run_id},
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

    def _publish_with_retries(self, **kwargs) -> str:
        last_error: Exception | None = None
        for attempt in range(1, settings.publish_max_retries + 1):
            try:
                return self._publish_once(**kwargs)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Publication attempt failed",
                    extra={"event_type": "publication.retry", "session_id": kwargs["session"].id},
                    exc_info=True,
                )
                if attempt < settings.publish_max_retries:
                    time.sleep(min(attempt, 3))
        assert last_error is not None
        raise last_error

    def _publish_once(self, db: Session, session: ReviewSession, target_system: str, target_object_id: str, external_comment_id: str | None, body_markdown: str) -> str:
        if target_system == "jira":
            return self._publish_jira(db, session, target_object_id, external_comment_id, body_markdown)
        if target_system == "gitlab":
            return self._publish_gitlab(db, session, target_object_id, external_comment_id, body_markdown)
        if target_system == "confluence":
            return self._publish_confluence(db, session, target_object_id, external_comment_id, body_markdown)
        if target_system == "manual":
            return external_comment_id or "manual-comment"
        raise ValueError(f"Unsupported target_system: {target_system}")

    def _get_credential(self, db: Session, *, session: ReviewSession, expected_type: str) -> ConnectorCredential:
        credential_id = session.source_object.connector_credential_id
        if credential_id is None:
            raise ValueError(f"{expected_type} source object is missing connector credential")
        credential = db.get(ConnectorCredential, credential_id)
        if credential is None or credential.connector_type != expected_type or not credential.is_active:
            raise ValueError(f"Active {expected_type} connector credential not found")
        return credential

    def _publish_jira(self, db: Session, session: ReviewSession, issue_key: str, external_comment_id: str | None, body_markdown: str) -> str:
        credential = self._get_credential(db, session=session, expected_type="jira")
        token = CryptoService().decrypt(credential.secret_encrypted)
        jira = JiraClient(base_url=credential.base_url, token=token)
        if external_comment_id:
            jira.update_comment(issue_key=issue_key, comment_id=external_comment_id, body=body_markdown)
            return external_comment_id
        return jira.create_comment(issue_key=issue_key, body=body_markdown)

    def _publish_gitlab(self, db: Session, session: ReviewSession, target_object_id: str, external_comment_id: str | None, body_markdown: str) -> str:
        credential = self._get_credential(db, session=session, expected_type="gitlab")
        token = CryptoService().decrypt(credential.secret_encrypted)
        gitlab = GitLabClient(base_url=credential.base_url, token=token)
        project_id, mr_iid = gitlab.parse_external_id(target_object_id)
        if external_comment_id:
            gitlab.update_note(project_id=project_id, mr_iid=mr_iid, note_id=external_comment_id, body=body_markdown)
            return external_comment_id
        return gitlab.create_note(project_id=project_id, mr_iid=mr_iid, body=body_markdown)

    def _publish_confluence(self, db: Session, session: ReviewSession, page_id: str, external_comment_id: str | None, body_markdown: str) -> str:
        credential = self._get_credential(db, session=session, expected_type="confluence")
        token = CryptoService().decrypt(credential.secret_encrypted)
        confluence = ConfluenceClient(base_url=credential.base_url, token=token, auth_type=credential.auth_type)
        if external_comment_id:
            confluence.update_comment(page_id=page_id, comment_id=external_comment_id, body=body_markdown)
            return external_comment_id
        return confluence.create_comment(page_id=page_id, body=body_markdown)
