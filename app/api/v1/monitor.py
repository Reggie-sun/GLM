from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.monitor.scheduler import get_monitor_scheduler
from app.monitor.tasks import MonitorTask, TaskStatus, get_task_registry

router = APIRouter(tags=["monitor"])


# Request schemas
class CreateMonitorTaskRequest(BaseModel):
    name: str = Field(..., description="Name of the monitor task")
    target_url: str = Field(..., description="URL to monitor")
    check_interval: int = Field(30, description="Check interval in seconds", ge=5)
    auto_purchase: bool = Field(False, description="Whether to auto-purchase when in stock")
    account_id: Optional[int] = Field(None, description="Account ID to use for purchase")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")


class UpdateMonitorTaskRequest(BaseModel):
    name: Optional[str] = None
    check_interval: Optional[int] = Field(None, ge=5)
    auto_purchase: Optional[bool] = None


# Response schemas
class MonitorTaskResponse(BaseModel):
    task_id: str
    name: str
    target_url: str
    status: str
    check_interval: int
    auto_purchase: bool
    account_id: Optional[int] = None
    webhook_url: Optional[str] = None
    created_at: str
    last_run_at: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class SimpleResponse(BaseModel):
    success: bool
    message: str


def _task_to_response(task: MonitorTask) -> MonitorTaskResponse:
    """Convert MonitorTask to response model"""
    return MonitorTaskResponse(
        task_id=task.task_id,
        name=task.name,
        target_url=task.target_url,
        status=task.status.value,
        check_interval=task.check_interval,
        auto_purchase=task.auto_purchase,
        account_id=task.account_id,
        webhook_url=task.webhook_url,
        created_at=task.created_at.isoformat(),
        last_run_at=task.last_run_at.isoformat() if task.last_run_at else None,
        last_result=task.last_result,
        error_message=task.error_message,
    )


@router.get("/tasks", response_model=List[MonitorTaskResponse])
async def list_monitor_tasks():
    """List all monitor tasks"""
    registry = get_task_registry()
    tasks = registry.list_all()
    return [_task_to_response(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=MonitorTaskResponse)
async def get_monitor_task(task_id: str):
    """Get a monitor task by ID"""
    registry = get_task_registry()
    task = registry.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.post("/tasks", response_model=MonitorTaskResponse)
async def create_monitor_task(request: CreateMonitorTaskRequest):
    """Create a new monitor task"""
    scheduler = get_monitor_scheduler()

    task = MonitorTask(
        task_id="",  # will be auto-generated
        name=request.name,
        target_url=request.target_url,
        check_interval=request.check_interval,
        auto_purchase=request.auto_purchase,
        account_id=request.account_id,
        webhook_url=request.webhook_url,
    )

    task_id = await scheduler.start_monitor(task)
    created_task = scheduler.get_task(task_id)

    return _task_to_response(created_task)


@router.post("/tasks/{task_id}/start", response_model=SimpleResponse)
async def start_monitor_task(task_id: str):
    """Start a monitor task"""
    scheduler = get_monitor_scheduler()
    task = scheduler.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == TaskStatus.RUNNING:
        return SimpleResponse(success=False, message="Task already running")

    await scheduler.start_monitor(task)
    return SimpleResponse(success=True, message="Task started")


@router.post("/tasks/{task_id}/stop", response_model=SimpleResponse)
async def stop_monitor_task(task_id: str):
    """Stop a monitor task"""
    scheduler = get_monitor_scheduler()
    success = await scheduler.stop_monitor(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return SimpleResponse(success=True, message="Task stopped")


@router.delete("/tasks/{task_id}", response_model=SimpleResponse)
async def delete_monitor_task(task_id: str):
    """Delete a monitor task"""
    scheduler = get_monitor_scheduler()
    await scheduler.stop_monitor(task_id)

    registry = get_task_registry()
    success = registry.remove(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    return SimpleResponse(success=True, message="Task deleted")


@router.post("/tasks/{task_id}/trigger-purchase", response_model=Dict[str, Any])
async def trigger_purchase(task_id: str):
    """Manually trigger purchase attempt"""
    scheduler = get_monitor_scheduler()
    task = scheduler.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return await scheduler._attempt_purchase(task)


@router.post("/tasks/{task_id}/check", response_model=Dict[str, Any])
async def check_stock_once(task_id: str):
    """Check stock status once manually"""
    scheduler = get_monitor_scheduler()
    task = scheduler.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await scheduler._check_stock_once(task)
    return result


@router.get("/status", response_model=Dict[str, Any])
async def get_scheduler_status():
    """Get scheduler status"""
    scheduler = get_monitor_scheduler()
    registry = get_task_registry()

    all_tasks = registry.list_all()
    running_count = sum(1 for t in all_tasks if t.status == TaskStatus.RUNNING)

    return {
        "total_tasks": len(all_tasks),
        "running_tasks": running_count,
        "is_running": scheduler._running,
    }


@router.post("/scheduler/start", response_model=SimpleResponse)
async def start_scheduler():
    """Start the monitor scheduler"""
    scheduler = get_monitor_scheduler()
    await scheduler.start()
    return SimpleResponse(success=True, message="Scheduler started")


@router.post("/scheduler/stop", response_model=SimpleResponse)
async def stop_scheduler():
    """Stop the monitor scheduler"""
    scheduler = get_monitor_scheduler()
    await scheduler.stop()
    return SimpleResponse(success=True, message="Scheduler stopped")
