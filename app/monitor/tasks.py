import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class MonitorTask:
    task_id: str
    name: str
    target_url: str
    check_interval: int  # seconds
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = datetime.now()
    last_run_at: Optional[datetime] = None
    last_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    auto_purchase: bool = False
    on_stock_change: Optional[Callable] = None

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid4())


class MonitorTaskRegistry:
    def __init__(self):
        self._tasks: Dict[str, MonitorTask] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def add(self, task: MonitorTask) -> str:
        """Add a monitor task"""
        self._tasks[task.task_id] = task
        return task.task_id

    def get(self, task_id: str) -> Optional[MonitorTask]:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def list_all(self) -> list[MonitorTask]:
        """List all tasks"""
        return list(self._tasks.values())

    def remove(self, task_id: str) -> bool:
        """Remove a task"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]
            return True
        return False

    def update_status(self, task_id: str, status: TaskStatus, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update task status"""
        task = self.get(task_id)
        if task:
            task.status = status
            if result is not None:
                task.last_result = result
            if error is not None:
                task.error_message = error
            if status == TaskStatus.RUNNING:
                task.last_run_at = datetime.now()

    def is_running(self, task_id: str) -> bool:
        """Check if task is running"""
        return task_id in self._running_tasks


# Global task registry
_task_registry: Optional[MonitorTaskRegistry] = None


def get_task_registry() -> MonitorTaskRegistry:
    """Get the global task registry"""
    global _task_registry
    if not _task_registry:
        _task_registry = MonitorTaskRegistry()
    return _task_registry
