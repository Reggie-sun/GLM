from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True, index=True)
    proxy_type = Column(String(20), default="http")  # http, https, socks5
    host = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100))
    password = Column(String(255))
    status = Column(String(20), default="active")  # active, inactive, error
    last_checked_at = Column(DateTime(timezone=True))
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_public = Column(Boolean, default=True)  # True=公共池, False=用户私有
    owner_id = Column(Integer, nullable=True)
