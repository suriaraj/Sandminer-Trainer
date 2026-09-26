"""Celery worker and beat schedules; run beat as a separate process in production."""
from celery import Celery

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.expiry import release_expired_holds

settings = get_settings()
celery_app = Celery("pyro", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "expire-unpaid-booking-holds": {
            "task": "bookings.expire_unpaid_holds",
            "schedule": 60.0,
        }
    },
)


@celery_app.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="bookings.expire_unpaid_holds")
def expire_unpaid_holds() -> int:
    with SessionLocal() as db:
        count = release_expired_holds(db)
        db.commit()
        return count
