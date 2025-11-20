#!/bin/bash

export REDIS_URL="redis://localhost:6379/0"

echo "Starting Redis server..."
redis-server --daemonize yes --port 6379 --bind 127.0.0.1

sleep 2

echo "Starting Celery worker..."
celery -A app.celery_app worker --loglevel=info --concurrency=2 --detach

sleep 2

echo "Starting FastAPI application..."
uvicorn app.main:app --host 0.0.0.0 --port 5000
