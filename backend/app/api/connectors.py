from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.connectors.confluence_client import ConfluenceClient
from app.connectors.gitlab_client import GitLabClient
from app.connectors.jira_client import JiraClient
from app.db import get_db
from app.models.connector_credential import ConnectorCredential
from app.schemas.connectors import ConnectorCreateRequest, ConnectorResponse, ConnectorTestResponse
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService

router = APIRouter(prefix='/connectors', tags=['connectors'])


@router.get('', response_model=list[ConnectorResponse])
def list_connectors(db: Session = Depends(get_db)) -> list[ConnectorCredential]:
    return db.query(ConnectorCredential).order_by(ConnectorCredential.created_at.desc()).all()


@router.post('', response_model=ConnectorResponse)
def create_connector(payload: ConnectorCreateRequest, db: Session = Depends(get_db)) -> ConnectorCredential:
    crypto = CryptoService()
    item = ConnectorCredential(
        connector_type=payload.connector_type,
        name=payload.name,
        base_url=payload.base_url,
        auth_type=payload.auth_type,
        secret_encrypted=crypto.encrypt(payload.secret_plain),
        is_active=True,
    )
    db.add(item)
    db.flush()
    AuditService().log(
        db,
        event_type='connector.created',
        entity_type='connector_credential',
        entity_id=item.id,
        payload={'connector_type': item.connector_type, 'name': item.name, 'base_url': item.base_url},
    )
    db.commit()
    db.refresh(item)
    return item


@router.post('/{connector_id}/test', response_model=ConnectorTestResponse)
def test_connector(connector_id: UUID, db: Session = Depends(get_db)) -> ConnectorTestResponse:
    connector = db.get(ConnectorCredential, connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail='Connector not found')
    if not connector.is_active:
        raise HTTPException(status_code=400, detail='Connector is inactive')

    secret = CryptoService().decrypt(connector.secret_encrypted)

    if connector.connector_type == 'jira':
        details = JiraClient(
            base_url=connector.base_url,
            token=secret,
            auth_type=connector.auth_type,
        ).test_connection()
        display_name = details.get('display_name') or details.get('account_id') or 'unknown'
        result = ConnectorTestResponse(ok=True, connector_type='jira', details=f'Connected as {display_name}')
    elif connector.connector_type == 'gitlab':
        details = GitLabClient(base_url=connector.base_url, token=secret).test_connection()
        display_name = details.get('username') or details.get('name') or 'unknown'
        result = ConnectorTestResponse(ok=True, connector_type='gitlab', details=f'Connected as {display_name}')
    elif connector.connector_type == 'confluence':
        details = ConfluenceClient(base_url=connector.base_url, token=secret, auth_type=connector.auth_type).test_connection()
        base = details.get('base') or connector.base_url
        result = ConnectorTestResponse(ok=True, connector_type='confluence', details=f'Connected to {base}')
    else:
        raise HTTPException(status_code=400, detail='Unsupported connector type')

    AuditService().log(
        db,
        event_type='connector.tested',
        entity_type='connector_credential',
        entity_id=connector.id,
        payload={'connector_type': connector.connector_type, 'ok': True},
    )
    db.commit()
    return result
