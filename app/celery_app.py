from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "glm_coding_bot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.celery_tasks"])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task"""
    print(f"Request: {self.request!r}")
    return "OK"
