#!/usr/bin/env bash
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is required. This project is PostgreSQL-only." >&2
  exit 1
fi

python manage.py check --deploy
python manage.py collectstatic --noinput
python manage.py migrate --noinput
echo "Django PostgreSQL deployment checks completed."
