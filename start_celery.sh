#!/bin/bash
export REDIS_URL="redis://localhost:6379/0"
celery -A app.celery_app worker --loglevel=info --concurrency=2
