import asyncio
from typing import Dict, Any
from celery import shared_task

from app.celery_app import celery_app
from app.monitor.scheduler import get_monitor_scheduler
from app.monitor.tasks import MonitorTask, TaskStatus


@shared_task(name="monitor.check_stock")
def check_stock_task(task_id: str) -> Dict[str, Any]:
    """Check stock for a monitor task"""
    # Note: Celery tasks run in a separate process and are synchronous
    # For async code, we need to run it in an event loop

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        scheduler = get_monitor_scheduler()
        task = scheduler.get_task(task_id)

        if not task:
            return {"error": f"Task not found: {task_id}"}

        result = loop.run_until_complete(scheduler._check_stock_once(task))
        return result

    except Exception as e:
        return {"error": str(e)}

    finally:
        loop.close()


@shared_task(name="monitor.purchase")
def purchase_task(task_id: str) -> Dict[str, Any]:
    """Attempt purchase for a monitor task"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        scheduler = get_monitor_scheduler()
        task = scheduler.get_task(task_id)

        if not task:
            return {"error": f"Task not found: {task_id}"}

        result = loop.run_until_complete(scheduler._attempt_purchase(task))
        return result

    except Exception as e:
        return {"error": str(e)}

    finally:
        loop.close()
