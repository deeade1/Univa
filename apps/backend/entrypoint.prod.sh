#!/bin/sh
set -e

# Wait for PostgreSQL
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for PostgreSQL at $PGHOST:$PGPORT..."
    for i in $(seq 1 30); do
        if python -c "import socket; socket.create_connection((\"$PGHOST\", int(\"$PGPORT\")), timeout=5)" 2>/dev/null; then
            echo "PostgreSQL is ready!"
            break
        fi
        echo "Still waiting for PostgreSQL... ($i/30)"
        sleep 2
    done
fi

# Wait for Redis
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis at ${REDIS_HOST:-redis}:${REDIS_PORT:-6379}..."
    for i in $(seq 1 30); do
        if python -c "import socket; socket.create_connection((\"${REDIS_HOST:-redis}\", int(\"${REDIS_PORT:-6379}\")), timeout=5)" 2>/dev/null; then
            echo "Redis is ready!"
            break
        fi
        echo "Still waiting for Redis... ($i/30)"
        sleep 2
    done
fi

echo "Starting main process..."
exec "$@"
