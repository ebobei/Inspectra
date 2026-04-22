from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def log(self, db: Session, *, event_type: str, entity_type: str, entity_id, payload: dict) -> None:
        db.add(
            AuditLog(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                payload_json=payload,
            )
        )
        db.flush()
