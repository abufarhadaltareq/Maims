#!/usr/bin/env bash
#
# Copy existing data from the legacy SQLite database (db.sqlite3) into the
# PostgreSQL database configured via DATABASE_URL / POSTGRES_*.
#
# Usage (from anywhere):
#   ./scripts/migrate_sqlite_to_postgres.sh [dump-file]
#
# It relies on Django's dumpdata/loaddata, so no extra tooling is required.
# The dump step forces DB_ENGINE=sqlite (the app itself now defaults to
# PostgreSQL); the migrate + loaddata steps use the normal PostgreSQL settings.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../maims-project/backend" && pwd)"
DUMP_FILE="${1:-sqlite_dump.json}"

cd "$BACKEND_DIR"

# Prefer an explicit PYTHON, then the project venv, then python3.
if [ -z "${PYTHON:-}" ]; then
  if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
    PY="$BACKEND_DIR/.venv/bin/python"
  else
    PY="python3"
  fi
else
  PY="$PYTHON"
fi

if [ ! -f db.sqlite3 ]; then
  echo "ERROR: $BACKEND_DIR/db.sqlite3 not found." >&2
  echo "Nothing to migrate — set up PostgreSQL and run 'python manage.py migrate'." >&2
  exit 1
fi

echo "==> 1/3 Dumping data from SQLite -> $DUMP_FILE"
# contenttypes/permissions/sessions/admin log are schema-derived and regenerated
# by 'migrate' on the target, so they are excluded to avoid PK conflicts.
DB_ENGINE=sqlite "$PY" manage.py dumpdata \
  --natural-foreign --natural-primary \
  --exclude contenttypes \
  --exclude auth.permission \
  --exclude sessions \
  --exclude admin.logentry \
  -o "$DUMP_FILE"

echo "==> 2/3 Creating the PostgreSQL schema"
"$PY" manage.py migrate --noinput

echo "==> 3/3 Loading data into PostgreSQL"
"$PY" manage.py loaddata "$DUMP_FILE"

cat <<EOF

Done. Data copied into PostgreSQL.

Next steps:
  - Spot-check the data:   $PY manage.py shell -c "from products.models import Product; print(Product.objects.count())"
  - Give staff/superusers back their explicit permissions in /admin/ if needed.
  - Once verified, remove the temporary dump:  rm "$DUMP_FILE"
EOF
