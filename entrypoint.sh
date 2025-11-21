#!/bin/bash
set -e

echo "Starting application..."

# Only wait for PostgreSQL if DB_HOST is set (Docker Compose)
if [ -n "$DB_HOST" ]; then
    echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
    until nc -z "${DB_HOST}" "${DB_PORT:-5432}" 2>/dev/null; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "PostgreSQL is ready!"
fi

# Initialize database
echo "Initializing database..."
python -c "from app.database import init_db; init_db()" || echo "Database initialization skipped or failed"

echo "Starting application..."
exec "$@"
