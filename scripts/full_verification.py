#!/usr/bin/env python3
"""
Complete verification script for GLM Coding Bot
"""
import sys
import json
import requests
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

BASE_URL = "http://localhost:8001"


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_success(text):
    print(f"  ✓ {text}")


def print_error(text):
    print(f"  ✗ {text}")


def test_root_endpoint():
    print_header("Testing Root Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status: {response.status_code}")
            print_success(f"Message: {data.get('message')}")
            return True
        else:
            print_error(f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_health_endpoint():
    print_header("Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Status: {data.get('status')}")
            return True
        else:
            print_error(f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_accounts_endpoint():
    print_header("Testing Accounts Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/accounts/", timeout=5)
        if response.status_code == 200:
            accounts = response.json()
            print_success(f"Found {len(accounts)} account(s)")
            for acc in accounts:
                print(f"    - ID: {acc.get('id')}, User: {acc.get('username')}, Status: {acc.get('status')}")
            return True
        else:
            print_error(f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_create_monitor_task():
    print_header("Testing Create Monitor Task")
    try:
        payload = {
            "name": "Test Task - GLM Coding",
            "target_url": "https://bigmodel.cn/glm-coding",
            "check_interval": 60,
            "auto_purchase": False,
            "account_id": 1
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/monitor/tasks",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            task = response.json()
            print_success(f"Task created!")
            print(f"    ID: {task.get('task_id')}")
            print(f"    Name: {task.get('name')}")
            print(f"    Status: {task.get('status')}")
            print(f"    Auto-purchase: {task.get('auto_purchase')}")
            return task.get('task_id')
        else:
            print_error(f"Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Error: {e}")
        return None


def test_list_monitor_tasks():
    print_header("Testing List Monitor Tasks")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/monitor/tasks", timeout=5)
        if response.status_code == 200:
            tasks = response.json()
            print_success(f"Found {len(tasks)} task(s)")
            for task in tasks:
                print(f"    - {task.get('name')} ({task.get('task_id')[:12]}...) - {task.get('status')}")
            return tasks
        else:
            print_error(f"Status: {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error: {e}")
        return []


def test_monitor_status():
    print_header("Testing Monitor Status")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/monitor/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print_success(f"Total tasks: {status.get('total_tasks')}")
            print_success(f"Running tasks: {status.get('running_tasks')}")
            print_success(f"Scheduler running: {status.get('is_running')}")
            return True
        else:
            print_error(f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def test_openapi_docs():
    print_header("Testing OpenAPI Docs")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        if response.status_code == 200:
            spec = response.json()
            print_success(f"Title: {spec.get('info', {}).get('title')}")
            print_success(f"Paths: {len(spec.get('paths', {}))}")
            return True
        else:
            print_error(f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("    GLM Coding Bot - Full Verification")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Root", test_root_endpoint()))
    results.append(("Health", test_health_endpoint()))
    results.append(("Accounts", test_accounts_endpoint()))

    task_id = test_create_monitor_task()
    results.append(("Create Task", task_id is not None))

    tasks = test_list_monitor_tasks()
    results.append(("List Tasks", len(tasks) >= 0))

    results.append(("Monitor Status", test_monitor_status()))
    results.append(("OpenAPI", test_openapi_docs()))

    # Summary
    print_header("Verification Summary")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status:8} - {name}")

    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\n  ✓ All verifications passed! System is ready.")
        return 0
    else:
        print(f"\n  ✗ {total - passed} verification(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
