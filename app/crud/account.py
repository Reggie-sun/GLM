from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.account import Account


class CRUDAccount(CRUDBase):
    def get_by_username(self, db: Session, *, username: str) -> Optional[Account]:
        return db.query(Account).filter(Account.username == username).first()

    def get_active_public(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Account]:
        return db.query(Account).filter(
            Account.status == "active",
            Account.is_public == True
        ).offset(skip).limit(limit).all()

    def get_by_owner(self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100) -> List[Account]:
        return db.query(Account).filter(
            Account.owner_id == owner_id
        ).offset(skip).limit(limit).all()


account = CRUDAccount(Account)
