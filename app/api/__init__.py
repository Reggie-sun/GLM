from fastapi import APIRouter
from app.api.v1 import users, accounts, proxies, monitor

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(proxies.router, prefix="/proxies", tags=["proxies"])
api_router.include_router(monitor.router, prefix="/monitor", tags=["monitor"])
