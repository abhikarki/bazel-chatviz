from celery import Celery
from app.core.config import settings

# creating a celery instance with the address of the broker and where the result of a task should be put
app = Celery(
    "src",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)