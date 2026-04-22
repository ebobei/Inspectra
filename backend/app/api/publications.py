from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.publication import Publication
from app.schemas.publications import PublicationResponse

router = APIRouter(prefix="/publications", tags=["publications"])


@router.get("", response_model=list[PublicationResponse])
def list_publications(db: Session = Depends(get_db)) -> list[Publication]:
    return db.query(Publication).order_by(Publication.created_at.desc()).all()
