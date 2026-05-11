import asyncio
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.monitor.tasks import MonitorTask, TaskStatus, get_task_registry
from app.database import get_db
from app.crud import account
from app.models.account import Account
from bot.browser import BrowserManager
from bot.pages.bigmodel import BigModelPage, create_bigmodel_page
from bot.pages.bigmodel import StockStatus
from app.notifications import (
    get_notification_service,
    Notification,
    NotificationLevel,
    WebhookNotificationChannel,
)

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
        if self.browser_manager:
            await self.browser_manager.close()
            self.browser_manager = None
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

        while task.status == TaskStatus.RUNNING:
            if not self._running:
                await asyncio.sleep(0.1)
                continue

            try:
                logger.info(f"Checking stock for task: {task.name}")

                result = await self._check_stock_once(task)

                current_status = result.get("status")

                # Check for status change
                if last_status is not None and current_status != last_status:
                    logger.info(f"Stock status changed: {last_status} -> {current_status}")

                    await self._notify_stock_change(task, last_status, current_status, result)

                    # Call status change callback if any
                    if task.on_stock_change:
                        try:
                            await task.on_stock_change(last_status, current_status)
                        except Exception as e:
                            logger.error(f"Error in stock change callback: {e}")

                if current_status != StockStatus.IN_STOCK:
                    task.purchase_attempted = False

                if task.auto_purchase and current_status == StockStatus.IN_STOCK and not task.purchase_attempted:
                    logger.info(f"Stock available, attempting purchase: {task.name}")
                    purchase_result = await self._attempt_purchase(task)
                    task.purchase_attempted = True
                    result["purchase_result"] = purchase_result

                last_status = current_status
                self._registry.update_status(task.task_id, TaskStatus.RUNNING, result)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                self._registry.update_status(task.task_id, TaskStatus.FAILED, error=str(e))

            await asyncio.sleep(task.check_interval)

    async def _check_stock_once(self, task: MonitorTask) -> Dict[str, Any]:
        """Check stock once - navigates to GLM Coding page"""
        db_generator = None
        try:
            # Create browser context and page
            browser_manager = await self._get_or_create_browser_manager()
            context = await browser_manager.create_context()
            page = await create_bigmodel_page(context)

            if task.account_id:
                db_generator = get_db()
                db: Session = next(db_generator)
                db_account = account.get(db, id=task.account_id)

                if db_account and db_account.status == "active":
                    login_success = await self._login_page_with_account(page, db_account)
                    if not login_success:
                        await context.close()
                        return {
                            "status": StockStatus.UNKNOWN,
                            "error": f"Account {db_account.username} login failed during stock check",
                            "checked_at": datetime.now().isoformat(),
                        }

            # Navigate to GLM Coding product page and check
            await page.go_to_glm_coding()
            status, product_info = await page.check_stock()

            await context.close()

            result = {
                "status": status,
                "product": product_info.name,
                "price": product_info.price,
                "restock_time": product_info.restock_time,
                "checked_at": datetime.now().isoformat(),
            }

            # Log what we found
            logger.info(f"Check result: {status}")
            if product_info.restock_time:
                logger.info(f"Restock time: {product_info.restock_time}")

            return result

        except Exception as e:
            logger.error(f"Error checking stock: {e}")
            return {
                "status": StockStatus.UNKNOWN,
                "error": str(e),
                "checked_at": datetime.now().isoformat(),
            }
        finally:
            if db_generator is not None and hasattr(db_generator, "close"):
                db_generator.close()

    async def _attempt_purchase(self, task: MonitorTask) -> Dict[str, Any]:
        """Attempt purchase"""
        db_generator = None
        try:
            logger.info(f"Attempting purchase for task: {task.name}")

            # Get account from database
            if not task.account_id:
                result = {
                    "success": False,
                    "message": "No account configured for purchase",
                    "attempted_at": datetime.now().isoformat(),
                }
            else:
                db_generator = get_db()
                db: Session = next(db_generator)
                db_account = account.get(db, id=task.account_id)

                if not db_account:
                    result = {
                        "success": False,
                        "message": f"Account {task.account_id} not found",
                        "attempted_at": datetime.now().isoformat(),
                    }
                elif db_account.status != "active":
                    result = {
                        "success": False,
                        "message": f"Account {db_account.username} is not active",
                        "attempted_at": datetime.now().isoformat(),
                    }
                else:
                    # Execute purchase flow
                    result = await self._execute_purchase_flow(task, db_account)

                    # Update account last used time
                    db_account.last_used_at = datetime.now()
                    db.commit()

            # Send notification
            try:
                notification_service = get_notification_service()

                if result.get("success"):
                    notification = Notification(
                        title="Purchase Successful!",
                        message=f"Successfully purchased for task: {task.name}. Order ID: {result.get('order_id')}",
                        level=NotificationLevel.SUCCESS,
                    )
                else:
                    notification = Notification(
                        title="Purchase Failed",
                        message=f"Purchase attempt failed for task: {task.name}. Error: {result.get('message', result.get('error', 'Unknown error'))}",
                        level=NotificationLevel.ERROR,
                    )

                await notification_service.send(notification)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

            return result

        except Exception as e:
            logger.error(f"Error in purchase attempt: {e}")
            result = {
                "success": False,
                "error": str(e),
                "attempted_at": datetime.now().isoformat(),
            }

            # Send notification for unexpected exception
            try:
                notification_service = get_notification_service()
                notification = Notification(
                    title="Purchase Failed",
                    message=f"Purchase attempt failed for task: {task.name}. Error: {str(e)}",
                    level=NotificationLevel.ERROR,
                )
                await notification_service.send(notification)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

            return result
        finally:
            if db_generator is not None and hasattr(db_generator, "close"):
                db_generator.close()

    async def _notify_stock_change(
        self,
        task: MonitorTask,
        previous_status: StockStatus,
        current_status: StockStatus,
        result: Dict[str, Any],
    ) -> None:
        """Send a notification when a stock status changes."""
        try:
            notification = Notification(
                title="Stock Status Changed",
                message=(
                    f"{task.name} stock changed from "
                    f"{self._status_value(previous_status)} to {self._status_value(current_status)}"
                ),
                level=self._status_to_notification_level(current_status),
                data={
                    "task_id": task.task_id,
                    "task_name": task.name,
                    "target_url": task.target_url,
                    "product": result.get("product"),
                    "previous_status": self._status_value(previous_status),
                    "current_status": self._status_value(current_status),
                    "checked_at": result.get("checked_at"),
                },
            )

            notification_service = get_notification_service()
            await notification_service.send(notification)

            if task.webhook_url:
                webhook_channel = WebhookNotificationChannel(task.webhook_url)
                await webhook_channel.send(notification)
        except Exception as e:
            logger.error(f"Failed to send stock change notification: {e}")

    async def _execute_purchase_flow(self, task: MonitorTask, db_account: Account) -> Dict[str, Any]:
        """Execute the actual purchase flow with cookies"""
        try:
            # Create browser context and page
            browser_manager = await self._get_or_create_browser_manager()
            context = await browser_manager.create_context()
            page = await create_bigmodel_page(context)

            login_success = await self._login_page_with_account(page, db_account)

            if not login_success:
                await context.close()
                return {
                    "success": False,
                    "message": "Login failed with both cookies and password",
                    "attempted_at": datetime.now().isoformat(),
                }

            # Navigate to GLM Coding product page
            await page.go_to_glm_coding()
            await asyncio.sleep(2)

            # Attempt purchase
            purchase_success, order_id = await page.purchase()

            await context.close()

            return {
                "success": purchase_success,
                "order_id": order_id,
                "message": "Purchase successful" if purchase_success else "Purchase failed",
                "attempted_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in purchase flow: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "attempted_at": datetime.now().isoformat(),
            }

    async def _get_or_create_browser_manager(self) -> BrowserManager:
        """Create the browser manager lazily and reuse it across checks."""
        if not self.browser_manager:
            self.browser_manager = BrowserManager()
        return self.browser_manager

    async def _login_page_with_account(self, page: BigModelPage, db_account: Account) -> bool:
        """Authenticate a page with the account's cookies first, then password."""
        login_success = False

        if db_account.cookie:
            try:
                await page.go_to_home()
                await asyncio.sleep(1)
                cookies = json.loads(db_account.cookie)
                login_success = await page.login_with_cookies(cookies)
                logger.info("Cookie login attempted")
            except Exception as e:
                logger.warning(f"Cookie login failed: {e}")

        if not login_success and db_account.password:
            logger.info("Falling back to username/password login")
            login_success = await page.login(db_account.username, db_account.password)

        return login_success

    def get_task(self, task_id: str) -> Optional[MonitorTask]:
        """Get a task by ID"""
        return self._registry.get(task_id)

    def list_tasks(self) -> list[MonitorTask]:
        """List all tasks"""
        return self._registry.list_all()

    @staticmethod
    def _status_value(status: StockStatus | str) -> str:
        return status.value if isinstance(status, StockStatus) else str(status)

    @staticmethod
    def _status_to_notification_level(status: StockStatus | str) -> NotificationLevel:
        normalized = status if isinstance(status, StockStatus) else StockStatus(str(status))
        if normalized == StockStatus.IN_STOCK:
            return NotificationLevel.SUCCESS
        if normalized == StockStatus.OUT_OF_STOCK:
            return NotificationLevel.WARNING
        return NotificationLevel.ERROR


# Global scheduler instance
_scheduler: Optional[MonitorScheduler] = None


def get_monitor_scheduler() -> MonitorScheduler:
    """Get the global monitor scheduler instance"""
    global _scheduler
    if not _scheduler:
        _scheduler = MonitorScheduler()
    return _scheduler
