import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User, Account, Proxy, Snapshot, Task


def test_model_imports():
    """Test that all models can be imported correctly"""
    assert User is not None
    assert Account is not None
    assert Proxy is not None
    assert Snapshot is not None
    assert Task is not None


def test_model_tablenames():
    """Test that models have correct __tablename__"""
    assert User.__tablename__ == "users"
    assert Account.__tablename__ == "accounts"
    assert Proxy.__tablename__ == "proxies"
    assert Snapshot.__tablename__ == "snapshots"
    assert Task.__tablename__ == "tasks"


def test_model_columns():
    """Test that models have expected columns"""
    user_columns = [c.name for c in User.__table__.columns]
    assert "id" in user_columns
    assert "username" in user_columns
    assert "email" in user_columns
    assert "hashed_password" in user_columns

    account_columns = [c.name for c in Account.__table__.columns]
    assert "id" in account_columns
    assert "username" in account_columns
    assert "status" in account_columns

    proxy_columns = [c.name for c in Proxy.__table__.columns]
    assert "id" in proxy_columns
    assert "host" in proxy_columns
    assert "port" in proxy_columns
