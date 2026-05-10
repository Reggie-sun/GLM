#!/usr/bin/env python3
"""
Import cookies - to be run inside docker container
"""
import sys
import json

from app.database import SessionLocal
from app.models import Account


def parse_cookie_string(cookie_string: str) -> list:
    """Parse cookie string into list of cookie dicts"""
    cookies = []

    for part in cookie_string.split(';'):
        part = part.strip()
        if '=' in part:
            name, value = part.split('=', 1)
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': 'bigmodel.cn',
                    'path': '/',
                    'httpOnly': False,
                    'secure': True
                })

    return cookies


def update_account_cookies(account_id: int, cookie_string: str):
    """Update account with parsed cookies"""
    print("=" * 70)
    print("Importing Cookies")
    print("=" * 70)

    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            print(f"\n  ✗ Account {account_id} not found")
            return False

        cookies = parse_cookie_string(cookie_string)

        print(f"\n  ✓ Parsed {len(cookies)} cookies:")
        for cookie in cookies[:10]:
            print(f"    - {cookie['name']}")
        if len(cookies) > 10:
            print(f"    ... and {len(cookies) - 10} more")

        account.cookie = json.dumps(cookies, ensure_ascii=False)

        if 'bigmodel_token_production' in cookie_string:
            print("\n  ✓ Found authentication token!")

        db.commit()

        print(f"\n  ✓ Account {account_id} updated successfully!")
        print(f"  ✓ Username: {account.username}")
        print(f"  ✓ Status: {account.status}")

        return True

    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_cookies_in_docker.py <cookie_string> [account_id]")
        sys.exit(1)

    cookie_string = sys.argv[1]
    account_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    success = update_account_cookies(account_id, cookie_string)
    sys.exit(0 if success else 1)
