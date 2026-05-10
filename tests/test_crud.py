import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.crud import user, account, proxy
from app.models import User, Account, Proxy


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_crud_imports():
    """Test that CRUD modules can be imported"""
    assert user is not None
    assert account is not None
    assert proxy is not None


def test_user_crud_get(db_session):
    """Test CRUD user get operation (basic check)"""
    # Just verify the method exists and doesn't crash
    result = user.get(db_session, id=1)
    assert result is None  # We expect None since no data


def test_account_crud_get(db_session):
    """Test CRUD account get operation (basic check)"""
    result = account.get(db_session, id=1)
    assert result is None


def test_proxy_crud_get(db_session):
    """Test CRUD proxy get operation (basic check)"""
    result = proxy.get(db_session, id=1)
    assert result is None
