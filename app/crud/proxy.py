from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.proxy import Proxy


class CRUDProxy(CRUDBase):
    def get_active_public(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Proxy]:
        return db.query(Proxy).filter(
            Proxy.status == "active",
            Proxy.is_public == True
        ).offset(skip).limit(limit).all()

    def get_by_owner(self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100) -> List[Proxy]:
        return db.query(Proxy).filter(
            Proxy.owner_id == owner_id
        ).offset(skip).limit(limit).all()


proxy = CRUDProxy(Proxy)
