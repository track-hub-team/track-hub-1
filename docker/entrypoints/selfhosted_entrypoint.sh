#!/bin/bash
set -e

echo "⏳ Waiting for MariaDB to be ready..."
/app/scripts/wait-for-db.sh "$MARIADB_HOSTNAME" "$MARIADB_PORT"

echo "🧱 Applying database migrations..."
flask db upgrade || echo "⚠️ Migrations failed, continuing anyway..."

echo "🚀 Starting TrackHub with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 app:app --log-level info --timeout 3600
