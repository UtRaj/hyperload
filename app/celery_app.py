import os
from celery import Celery

# Get Redis URL with proper fallback for Railway
REDIS_URL = os.getenv("REDIS_URL")

# Handle Railway's different Redis variable names
if not REDIS_URL or not REDIS_URL.startswith(("redis://", "rediss://")):
    REDIS_URL = os.getenv("REDISURL")  # Railway alternative
    
if not REDIS_URL or not REDIS_URL.startswith(("redis://", "rediss://")):
    REDIS_URL = os.getenv("REDIS_PRIVATE_URL")  # Railway private network
    
if not REDIS_URL or not REDIS_URL.startswith(("redis://", "rediss://")):
    # Fallback for local development
    REDIS_URL = "redis://localhost:6379/0"
    print(f"WARNING: Using fallback Redis URL for Celery")

print(f"Celery Redis URL: {REDIS_URL[:20]}...")

celery_app = Celery(
    "product_importer",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
