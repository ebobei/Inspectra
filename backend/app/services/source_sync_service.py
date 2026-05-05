from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors.confluence_client import ConfluenceClient
from app.connectors.gitlab_client import GitLabClient
from app.connectors.jira_client import JiraClient
from app.models.connector_credential import ConnectorCredential
from app.models.review_session import ReviewSession
from app.models.source_object import SourceObject
from app.models.source_snapshot import SourceSnapshot
from app.services.crypto_service import CryptoService
from app.utils.hashing import sha256_text


class SourceSyncService:
    def _create_snapshot(
        self,
        db: Session,
        *,
        source_object: SourceObject,
        text: str,
        raw_payload: dict,
        metadata: dict | None = None,
        title: str | None = None,
        external_url: str | None = None,
    ) -> SourceSnapshot:
        latest = (
            db.query(SourceSnapshot)
            .filter(SourceSnapshot.source_object_id == source_object.id)
            .order_by(SourceSnapshot.version_no.desc())
            .first()
        )
        next_version = 1 if latest is None else latest.version_no + 1

        snapshot = SourceSnapshot(
            source_object_id=source_object.id,
            version_no=next_version,
            raw_payload_json=raw_payload,
            normalized_text=text,
            normalized_metadata_json=metadata or {},
            content_hash=sha256_text(text),
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(snapshot)

        if title is not None:
            source_object.title = title
        if external_url is not None:
            source_object.external_url = external_url

        db.flush()
        return snapshot

    def create_manual_snapshot(
        self,
        db: Session,
        *,
        source_object: SourceObject,
        text: str,
        raw_payload: dict,
        metadata: dict | None = None,
    ) -> SourceSnapshot:
        return self._create_snapshot(
            db,
            source_object=source_object,
            text=text,
            raw_payload=raw_payload,
            metadata=metadata,
            title=raw_payload.get('title'),
        )

    def sync_session_source(self, db: Session, *, session: ReviewSession) -> SourceSnapshot:
        source_object = session.source_object
        if source_object.external_system == 'jira':
            return self._create_jira_snapshot(db, source_object=source_object)
        if source_object.external_system == 'gitlab':
            return self._create_gitlab_snapshot(db, source_object=source_object)
        if source_object.external_system == 'confluence':
            return self._create_confluence_snapshot(db, source_object=source_object)
        raise ValueError(f'Unsupported source system for sync: {source_object.external_system}')

    def _get_active_credential(self, db: Session, *, source_object: SourceObject, expected_type: str) -> ConnectorCredential:
        if source_object.connector_credential_id is None:
            raise ValueError(f'{expected_type} source object is missing connector credential')

        credential = db.get(ConnectorCredential, source_object.connector_credential_id)
        if credential is None or credential.connector_type != expected_type or not credential.is_active:
            raise ValueError(f'Active {expected_type} connector credential not found')
        return credential

    def _create_jira_snapshot(self, db: Session, *, source_object: SourceObject) -> SourceSnapshot:
        credential = self._get_active_credential(db, source_object=source_object, expected_type='jira')
        token = CryptoService().decrypt(credential.secret_encrypted)
        jira = JiraClient(
            base_url=credential.base_url,
            token=token,
            auth_type=credential.auth_type,
        )
        issue_payload = jira.fetch_issue(source_object.external_id)
        title, normalized_text, metadata = jira.normalize_issue(issue_payload)

        browse_url = None
        issue_key = issue_payload.get('key')
        if issue_key:
            browse_url = f"{credential.base_url.rstrip('/')}/browse/{issue_key}"

        return self._create_snapshot(
            db,
            source_object=source_object,
            text=normalized_text,
            raw_payload=issue_payload,
            metadata=metadata,
            title=title,
            external_url=browse_url,
        )

    def _create_gitlab_snapshot(self, db: Session, *, source_object: SourceObject) -> SourceSnapshot:
        credential = self._get_active_credential(db, source_object=source_object, expected_type='gitlab')
        token = CryptoService().decrypt(credential.secret_encrypted)
        gitlab = GitLabClient(base_url=credential.base_url, token=token)
        project_id, mr_iid = gitlab.parse_external_id(source_object.external_id)
        mr_payload = gitlab.fetch_merge_request(project_id, mr_iid)
        title, normalized_text, metadata = gitlab.normalize_merge_request(mr_payload)
        return self._create_snapshot(
            db,
            source_object=source_object,
            text=normalized_text,
            raw_payload=mr_payload,
            metadata=metadata,
            title=title,
            external_url=mr_payload.get('web_url'),
        )

    def _create_confluence_snapshot(self, db: Session, *, source_object: SourceObject) -> SourceSnapshot:
        credential = self._get_active_credential(db, source_object=source_object, expected_type='confluence')
        token = CryptoService().decrypt(credential.secret_encrypted)
        confluence = ConfluenceClient(base_url=credential.base_url, token=token, auth_type=credential.auth_type)
        page_payload = confluence.fetch_page(source_object.external_id)
        title, normalized_text, metadata = confluence.normalize_page(page_payload)
        webui = (page_payload.get('_links') or {}).get('webui')
        external_url = f"{credential.base_url.rstrip('/')}{webui}" if webui else None
        return self._create_snapshot(
            db,
            source_object=source_object,
            text=normalized_text,
            raw_payload=page_payload,
            metadata=metadata,
            title=title,
            external_url=external_url,
        )
