import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.monitor.tasks import MonitorTask, TaskStatus, get_task_registry
from bot.browser import BrowserManager
from bot.pages.bigmodel import BigModelPage, create_bigmodel_page
from bot.pages.bigmodel import StockStatus

logger = logging.getLogger(__name__)


class MonitorScheduler:
    def __init__(self, browser_manager: Optional[BrowserManager] = None):
        self.browser_manager = browser_manager
        self._running: bool = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._registry = get_task_registry()

    async def start(self):
        """Start the scheduler"""
        self._running = True
        logger.info("Monitor scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        for task_id, task in list(self._tasks.items()):
            task.cancel()
            self._tasks.pop(task_id, None)
            self._registry.update_status(task_id, TaskStatus.STOPPED)
        logger.info("Monitor scheduler stopped")

    async def start_monitor(self, task: MonitorTask) -> str:
        """Start monitoring a task"""
        if task.task_id in self._tasks:
            return task.task_id

        self._registry.add(task)
        self._registry.update_status(task.task_id, TaskStatus.RUNNING)

        async_task = asyncio.create_task(self._monitor_loop(task))
        self._tasks[task.task_id] = async_task

        logger.info(f"Started monitor task: {task.name} ({task.task_id})")
        return task.task_id

    async def stop_monitor(self, task_id: str) -> bool:
        """Stop monitoring a task"""
        if task_id not in self._tasks:
            return False

        task = self._tasks.pop(task_id)
        task.cancel()
        self._registry.update_status(task_id, TaskStatus.STOPPED)
        logger.info(f"Stopped monitor task: {task_id}")
        return True

    async def _monitor_loop(self, task: MonitorTask):
        """Main monitoring loop"""
        last_status: Optional[StockStatus] = None

        while self._running and task.status == TaskStatus.RUNNING:
            try:
                logger.info(f"Checking stock for task: {task.name}")

                result = await self._check_stock_once(task)

                current_status = result.get("status")

                # Check for status change
                if last_status is not None and current_status != last_status:
                    logger.info(f"Stock status changed: {last_status} -> {current_status}")

                    # Call status change callback if any
                    if task.on_stock_change:
                        try:
                            await task.on_stock_change(last_status, current_status)
                        except Exception as e:
                            logger.error(f"Error in stock change callback: {e}")

                    # Auto purchase if enabled and in stock
                    if task.auto_purchase and current_status == StockStatus.IN_STOCK:
                        logger.info(f"Stock available, attempting purchase: {task.name}")
                        purchase_result = await self._attempt_purchase(task)
                        result["purchase_result"] = purchase_result

                last_status = current_status
                self._registry.update_status(task.task_id, TaskStatus.RUNNING, result)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                self._registry.update_status(task.task_id, TaskStatus.FAILED, error=str(e))

            await asyncio.sleep(task.check_interval)

    async def _check_stock_once(self, task: MonitorTask) -> Dict[str, Any]:
        """Check stock once"""
        try:
            # Create browser context and page
            if not self.browser_manager:
                from bot.browser import get_browser_manager
                self.browser_manager = get_browser_manager()

            context = await self.browser_manager.create_context()
            page = await create_bigmodel_page(context)

            # Navigate and check
            await page.go_to_home()
            status, product_info = await page.check_stock()

            await context.close()

            return {
                "status": status,
                "product": product_info.name,
                "price": product_info.price,
                "checked_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error checking stock: {e}")
            return {
                "status": StockStatus.UNKNOWN,
                "error": str(e),
                "checked_at": datetime.now().isoformat(),
            }

    async def _attempt_purchase(self, task: MonitorTask) -> Dict[str, Any]:
        """Attempt purchase"""
        try:
            logger.info(f"Attempting purchase for task: {task.name}")

            # This would need to be implemented with actual purchase logic
            # using account credentials from database

            return {
                "success": False,
                "message": "Purchase feature not fully implemented",
                "attempted_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in purchase attempt: {e}")
            return {
                "success": False,
                "error": str(e),
                "attempted_at": datetime.now().isoformat(),
            }

    def get_task(self, task_id: str) -> Optional[MonitorTask]:
        """Get a task by ID"""
        return self._registry.get(task_id)

    def list_tasks(self) -> list[MonitorTask]:
        """List all tasks"""
        return self._registry.list_all()


# Global scheduler instance
_scheduler: Optional[MonitorScheduler] = None


def get_monitor_scheduler() -> MonitorScheduler:
    """Get the global monitor scheduler instance"""
    global _scheduler
    if not _scheduler:
        _scheduler = MonitorScheduler()
    return _scheduler
