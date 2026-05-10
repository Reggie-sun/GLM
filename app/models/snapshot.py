from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    snapshot_type = Column(String(50), nullable=False)  # full, partial
    data = Column(JSON, nullable=False)
    file_path = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
