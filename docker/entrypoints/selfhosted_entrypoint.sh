#!/bin/bash
set -e

echo "⏳ Waiting for MariaDB to be ready..."

SSL_ARGS=""
if [ -n "$MARIADB_SSL_CA" ]; then
  echo "Using SSL with CA at $MARIADB_SSL_CA"
  SSL_ARGS="--ssl --ssl-ca=$MARIADB_SSL_CA"
fi

attempt=0
while true; do
  attempt=$((attempt+1))
  if mariadb \
      -h "$MARIADB_HOSTNAME" \
      -P "$MARIADB_PORT" \
      -u"$MARIADB_USER" \
      -p"$MARIADB_PASSWORD" \
      $SSL_ARGS \
      -e "SELECT 1" >/dev/null 2>&1; then
    echo "MariaDB is up ✅"
    break
  else
    echo "MariaDB is unavailable (attempt $attempt), last error:"
    mariadb \
      -h "$MARIADB_HOSTNAME" \
      -P "$MARIADB_PORT" \
      -u"$MARIADB_USER" \
      -p"$MARIADB_PASSWORD" \
      $SSL_ARGS \
      -e "SELECT 1" || true
    echo "Sleeping..."
    sleep 2
  fi
done

echo "🧱 Applying database migrations..."
flask db upgrade || echo "⚠️ Migrations failed, continuing anyway..."

echo "🚀 Starting TrackHub with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 app:app --log-level info --timeout 3600
