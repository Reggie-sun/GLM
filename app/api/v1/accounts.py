from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.crud import account

router = APIRouter()


@router.get("/", response_model=List[dict])
def get_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    accounts = account.get_multi(db, skip=skip, limit=limit)
    return [{"id": a.id, "username": a.username, "status": a.status, "is_public": a.is_public} for a in accounts]


@router.get("/public", response_model=List[dict])
def get_public_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    accounts = account.get_active_public(db, skip=skip, limit=limit)
    return [{"id": a.id, "username": a.username, "status": a.status} for a in accounts]


@router.get("/{account_id}", response_model=dict)
def get_account(account_id: int, db: Session = Depends(get_db)):
    db_account = account.get(db, id=account_id)
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "id": db_account.id,
        "username": db_account.username,
        "status": db_account.status,
        "is_public": db_account.is_public
    }
