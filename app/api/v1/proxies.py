from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Proxy
from app.crud import proxy

router = APIRouter()


@router.get("/", response_model=List[dict])
def get_proxies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    proxies = proxy.get_multi(db, skip=skip, limit=limit)
    return [{"id": p.id, "host": p.host, "port": p.port, "status": p.status} for p in proxies]


@router.get("/public", response_model=List[dict])
def get_public_proxies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    proxies = proxy.get_active_public(db, skip=skip, limit=limit)
    return [{"id": p.id, "host": p.host, "port": p.port, "latency_ms": p.latency_ms} for p in proxies]


@router.get("/{proxy_id}", response_model=dict)
def get_proxy(proxy_id: int, db: Session = Depends(get_db)):
    db_proxy = proxy.get(db, id=proxy_id)
    if db_proxy is None:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {
        "id": db_proxy.id,
        "host": db_proxy.host,
        "port": db_proxy.port,
        "status": db_proxy.status,
        "is_public": db_proxy.is_public
    }
