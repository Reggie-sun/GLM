#!/usr/bin/env python3
"""
Initialize database tables
"""
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.database import Base, engine
from app.models import Account, User, Proxy, Snapshot, Task


def init_db():
    print("=" * 70)
    print("Initializing Database Tables")
    print("=" * 70)

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("\n✓ Database tables created successfully!")

        # Print table names
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTables created:")
        for table in sorted(tables):
            print(f"  - {table}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_db()
