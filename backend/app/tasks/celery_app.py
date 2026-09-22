import os
import sys
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Initialize Celery application
celery_app = Celery(
    "odipks_construction_os",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.brief_tasks",
        "app.tasks.notification_tasks",
    ],
)

# Timezone and execution configuration
# Per config: CELERY_TIMEZONE = "Asia/Kolkata", CELERY_ENABLE_UTC = False
celery_app.conf.timezone = settings.CELERY_TIMEZONE
celery_app.conf.enable_utc = settings.CELERY_ENABLE_UTC

# Detect test execution environment
is_testing = bool(os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules)

# Celery application configuration
celery_app.conf.update(
    task_always_eager=is_testing or os.environ.get("CELERY_TASK_ALWAYS_EAGER", "False").lower() in ("true", "1", "yes"),
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
)

# Celery Beat schedule for daily 8:00 AM IST Executive Brief
celery_app.conf.beat_schedule = {
    "daily-morning-brief-8am": {
        "task": "app.tasks.brief_tasks.generate_morning_brief_task",
        "schedule": crontab(hour=8, minute=0),
    },
}
