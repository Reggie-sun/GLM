from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)  # Should be encrypted in production
    email = Column(String(100))
    phone = Column(String(50))
    status = Column(String(20), default="active")  # active, blocked, invalid
    cookie = Column(Text)
    user_agent = Column(String(255))
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_public = Column(Boolean, default=True)  # True=公共池, False=用户私有
    owner_id = Column(Integer, nullable=True)  # 用户私有账号的owner
