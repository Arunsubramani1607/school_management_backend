#!/bin/sh
set -eu

export APP_DATA_DIR="${APP_DATA_DIR:-/var/data}"
mkdir -p "$APP_DATA_DIR"

if [ "${RENDER:-}" = "true" ] || [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
    if [ -z "${DATABASE_URL:-}" ]; then
        echo "ERROR: Set DATABASE_URL to the demo PostgreSQL database before starting on Render."
        exit 1
    fi
    if ! mountpoint -q "$APP_DATA_DIR"; then
        echo "ERROR: Mount a persistent disk at $APP_DATA_DIR before starting on Render."
        exit 1
    fi
fi

export JSON_DATABASE_BACKUP="${JSON_DATABASE_BACKUP:-$APP_DATA_DIR/school_data_backup.json}"
export JSON_DATABASE_BACKUP_INTERVAL="${JSON_DATABASE_BACKUP_INTERVAL:-300}"

if ! mountpoint -q "$APP_DATA_DIR"; then
    echo "WARNING: $APP_DATA_DIR is not a mounted persistent disk; uploaded media and JSON backups may be lost on redeploy."
fi

python manage.py migrate --noinput
python manage.py restore_json_database
python manage.py bootstrap_super_admin
if [ "${DEMO_MODE:-false}" = "true" ]; then
    python manage.py seed_demo_school
fi
python manage.py backup_json_database || echo "WARNING: Initial JSON database backup failed."

(
    while true; do
        sleep "$JSON_DATABASE_BACKUP_INTERVAL"
        python manage.py backup_json_database || echo "WARNING: Scheduled JSON database backup failed."
    done
) &

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
