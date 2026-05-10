from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.task import Task


class CRUDTask(CRUDBase):
    def get_by_status(self, db: Session, *, status: str, skip: int = 0, limit: int = 100) -> List[Task]:
        return db.query(Task).filter(
            Task.status == status
        ).order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_creator(self, db: Session, *, created_by: int, skip: int = 0, limit: int = 100) -> List[Task]:
        return db.query(Task).filter(
            Task.created_by == created_by
        ).order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_pending(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Task]:
        return db.query(Task).filter(
            Task.status == "pending"
        ).order_by(Task.created_at.asc()).offset(skip).limit(limit).all()


task = CRUDTask(Task)
