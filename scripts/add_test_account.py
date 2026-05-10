#!/usr/bin/env python3
"""
Add test account to database
"""
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.database import SessionLocal
from app.models import Account


def add_test_account():
    print("=" * 70)
    print("Adding Test Account")
    print("=" * 70)

    db = SessionLocal()
    try:
        # Check if account already exists
        existing = db.query(Account).filter(Account.username == "test_user").first()
        if existing:
            print(f"\n✓ Test account already exists (ID: {existing.id})")
            return existing.id

        # Create test account
        test_account = Account(
            username="test_user",
            password_hash="test_password_hash",  # Placeholder - not used for real auth
            status="active",
            is_public=True,
            cookies={},  # Empty cookies - user needs to add real ones
            notes="Test account for auto-purchase verification"
        )
        db.add(test_account)
        db.commit()
        db.refresh(test_account)

        print(f"\n✓ Test account created successfully!")
        print(f"  ID: {test_account.id}")
        print(f"  Username: {test_account.username}")
        print(f"  Status: {test_account.status}")
        print(f"  Public: {test_account.is_public}")
        print(f"\n  Note: You need to add real cookies to use this account for purchases")

        return test_account.id

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    add_test_account()
