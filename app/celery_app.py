from celery import Celery
from app.core.config import settings

# Celery application
app = Celery(
    "chatapp",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Autodiscover tasks package
app.autodiscover_tasks(["app.tasks"])
