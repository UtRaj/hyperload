#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until nc -z $DB_HOST $DB_PORT; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - initializing database"
python -c "from app.database import init_db; init_db()"

echo "Starting application..."
exec "$@"
