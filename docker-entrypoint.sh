#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: Set DATABASE_URL to the PostgreSQL database before starting."
    exit 1
fi

python manage.py migrate --noinput
python manage.py bootstrap_super_admin
if [ "${DEMO_MODE:-false}" = "true" ]; then
    python manage.py seed_demo_school
fi

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
