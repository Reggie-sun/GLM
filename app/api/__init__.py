from fastapi import APIRouter
from app.api.v1 import users, accounts, proxies

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(proxies.router, prefix="/proxies", tags=["proxies"])
