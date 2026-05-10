#!/usr/bin/env python3
"""
Verify the auto-purchase feature is properly set up.
This script checks all the components without actually making a purchase.
"""
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

print("=" * 70)
print("GLM Coding Bot - Auto Purchase Verification")
print("=" * 70)

checks = []

# Check 1: Import all required modules
print("\n1. Checking imports...")
try:
    from app.monitor.scheduler import MonitorScheduler
    from app.monitor.tasks import MonitorTask
    from bot.pages.bigmodel import BigModelPage
    from app.crud import account
    print("   ✓ All imports successful")
    checks.append(("Imports", True))
except Exception as e:
    print(f"   ✗ Import error: {e}")
    checks.append(("Imports", False))

# Check 2: Verify MonitorTask has account_id
print("\n2. Checking MonitorTask structure...")
try:
    task = MonitorTask(
        task_id="test",
        name="Test",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )
    assert hasattr(task, "account_id")
    assert task.account_id == 1
    print("   ✓ MonitorTask has account_id field")
    checks.append(("MonitorTask Structure", True))
except Exception as e:
    print(f"   ✗ MonitorTask check failed: {e}")
    checks.append(("MonitorTask Structure", False))

# Check 3: Verify _attempt_purchase exists
print("\n3. Checking scheduler methods...")
try:
    scheduler = MonitorScheduler()
    assert hasattr(scheduler, "_attempt_purchase")
    assert hasattr(scheduler, "_execute_purchase_flow")
    print("   ✓ Scheduler has purchase methods")
    checks.append(("Scheduler Methods", True))
except Exception as e:
    print(f"   ✗ Scheduler check failed: {e}")
    checks.append(("Scheduler Methods", False))

# Check 4: Verify BigModelPage has login and purchase
print("\n4. Checking BigModelPage methods...")
try:
    from unittest.mock import Mock
    page = BigModelPage(Mock(), Mock())
    assert hasattr(page, "login")
    assert hasattr(page, "purchase")
    print("   ✓ BigModelPage has required methods")
    checks.append(("BigModelPage Methods", True))
except Exception as e:
    print(f"   ✗ BigModelPage check failed: {e}")
    checks.append(("BigModelPage Methods", False))

# Summary
print("\n" + "=" * 70)
print("Verification Summary")
print("=" * 70)

all_passed = True
for name, passed in checks:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status:10} {name}")
    if not passed:
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("✓ All verifications passed!")
    print("\nNext steps:")
    print("1. Make sure you have network access to bigmodel.cn")
    print("2. Analyze the page structure to get real selectors")
    print("3. Update bot/pages/bigmodel.py with real selectors")
    print("4. Add test accounts to the database")
    print("5. Test the full flow!")
else:
    print("✗ Some checks failed. Please fix the issues above.")
print("=" * 70)

sys.exit(0 if all_passed else 1)
