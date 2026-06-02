#!/usr/bin/env python3
"""
Import cookies into database account
"""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.database import SessionLocal
from app.models import Account


USAGE = """Usage:
  python import_cookies.py --stdin [account_id]
  python import_cookies.py --env COOKIE_ENV_VAR [account_id]
  python import_cookies.py '<cookie_string>' [account_id]

Prefer --stdin or --env so sensitive cookies do not appear in shell history or process args.
"""


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


def read_cookie_input(argv: list[str], stdin=sys.stdin, env=os.environ) -> tuple[str, int]:
    """Read cookie input from stdin, env, or the legacy positional argument."""
    if not argv:
        raise ValueError(USAGE)

    if argv[0] == "--stdin":
        cookie_string = stdin.read().strip()
        account_id = int(argv[1]) if len(argv) > 1 else 1
    elif argv[0] == "--env":
        if len(argv) < 2:
            raise ValueError(USAGE)
        env_var = argv[1]
        cookie_string = env.get(env_var, "").strip()
        account_id = int(argv[2]) if len(argv) > 2 else 1
    else:
        cookie_string = argv[0].strip()
        account_id = int(argv[1]) if len(argv) > 1 else 1

    if not cookie_string:
        raise ValueError("Cookie string is empty")

    return cookie_string, account_id


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
    try:
        cookie_string, account_id = read_cookie_input(sys.argv[1:])
    except ValueError as e:
        print(e)
        sys.exit(1)

    success = update_account_cookies(account_id, cookie_string)
    sys.exit(0 if success else 1)
