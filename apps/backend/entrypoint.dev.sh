#!/bin/bash
set -euo pipefail

# Environment variables with defaults
DB_HOST=${PGHOST:-kaz-db}
DB_PORT=${PGPORT:-5432}
PORT=${PORT:-8000}

# Wait for PostgreSQL
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
until python -c "import socket; s = socket.create_connection((\"$DB_HOST\", int(\"$DB_PORT\")), timeout=5)" 2>/dev/null; do
    echo "Still waiting for PostgreSQL..."
    sleep 2
done
echo "PostgreSQL is ready!"

# Wait for Redis
echo "Waiting for Redis at redis:6379..."
until python -c "import socket; s = socket.create_connection((\"redis\", 6379), timeout=5)" 2>/dev/null; do
    echo "Still waiting for Redis..."
    sleep 2
done
echo "Redis is ready!"

# Start Django dev server
echo "Starting Django development server on port $PORT..."
exec python manage.py runserver 0.0.0.0:$PORT
