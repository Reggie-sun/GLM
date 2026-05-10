from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.crud import user

router = APIRouter()


@router.get("/", response_model=List[dict])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = user.get_multi(db, skip=skip, limit=limit)
    return [{"id": u.id, "username": u.username, "email": u.email} for u in users]


@router.get("/{user_id}", response_model=dict)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": db_user.id, "username": db_user.username, "email": db_user.email}
