from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.snapshot import Snapshot


class CRUDSnapshot(CRUDBase):
    def get_latest(self, db: Session, *, snapshot_type: Optional[str] = None) -> Optional[Snapshot]:
        query = db.query(Snapshot)
        if snapshot_type:
            query = query.filter(Snapshot.snapshot_type == snapshot_type)
        return query.order_by(Snapshot.created_at.desc()).first()

    def get_by_type(self, db: Session, *, snapshot_type: str, skip: int = 0, limit: int = 100) -> List[Snapshot]:
        return db.query(Snapshot).filter(
            Snapshot.snapshot_type == snapshot_type
        ).order_by(Snapshot.created_at.desc()).offset(skip).limit(limit).all()


snapshot = CRUDSnapshot(Snapshot)
