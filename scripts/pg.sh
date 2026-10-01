#!/usr/bin/env bash
#
# Local PostgreSQL helper — no root and no Docker required.
#
# A self-contained PostgreSQL 18 distribution is unpacked under ~/.local/pgsql
# (binaries) with its data directory at ~/.local/pgsql/data. This script manages
# that single-node cluster on 127.0.0.1:5432, matching the DATABASE_URL in .env.
#
#   ./scripts/pg.sh start      start the server
#   ./scripts/pg.sh stop       stop the server
#   ./scripts/pg.sh restart    stop then start
#   ./scripts/pg.sh status     is it accepting connections?
#   ./scripts/pg.sh logs       tail the server log
#   ./scripts/pg.sh psql       psql session as maims_user@maims_db
#   ./scripts/pg.sh init       initialise the cluster + role/database
#   ./scripts/pg.sh ensure     start only if down (cron-safe, silent when healthy)
#
# Auto-start: this script is wired into the user's crontab with '@reboot' plus a
# periodic 'ensure' heartbeat, so the server comes back after a reboot or an
# unexpected crash. See DEPLOYMENT.md ("Keeping PostgreSQL running").
set -euo pipefail

# cron runs with a minimal environment; make sure the standard tools resolve.
PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PATH

PGROOT="${PGROOT:-$HOME/.local/pgsql}"
PGBIN="$PGROOT/usr/lib/postgresql/18/bin"
PGDATA="${PGDATA:-$PGROOT/data}"
PGPORT="${PGPORT:-5432}"
PGHOST="${PGHOST:-127.0.0.1}"
DB_NAME="${DB_NAME:-maims_db}"
DB_USER="${DB_USER:-maims_user}"
DB_PASSWORD="${DB_PASSWORD:-maims_password}"
LOGFILE="$PGDATA/server.log"
CRONLOG="$PGDATA/autostart.log"
SOCKETDIR="${SOCKETDIR:-${TMPDIR:-/tmp}}"

if [ ! -x "$PGBIN/pg_ctl" ]; then
  echo "ERROR: PostgreSQL binaries not found at $PGBIN" >&2
  echo "Run the setup described in DEPLOYMENT.md (the .deb packages are unpacked with dpkg-deb -x)." >&2
  exit 1
fi

start() {
  if "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
    echo "PostgreSQL is already running."
    return 0
  fi
  "$PGBIN/pg_ctl" -D "$PGDATA" -l "$LOGFILE" \
    -o "-p $PGPORT -k $SOCKETDIR -c listen_addresses=$PGHOST" -w start
}

stop() {
  "$PGBIN/pg_ctl" -D "$PGDATA" -m fast -w stop
}

init() {
  if [ -f "$PGDATA/PG_VERSION" ]; then
    echo "Cluster already initialised at $PGDATA"
  else
    "$PGBIN/initdb" -D "$PGDATA" -U postgres -E UTF8 --locale=C \
      --auth-local=trust --auth-host=scram-sha-256
  fi
  start
  # Single-user socket to the bootstrap superuser (trust auth) for admin SQL.
  "$PGBIN/psql" -h "$SOCKETDIR" -p "$PGPORT" -U postgres -d postgres -v ON_ERROR_STOP=1 \
    -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='$DB_USER') THEN CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD' CREATEDB; END IF; END \$\$;"
  if ! "$PGBIN/psql" -h "$SOCKETDIR" -p "$PGPORT" -U postgres -d postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    "$PGBIN/psql" -h "$SOCKETDIR" -p "$PGPORT" -U postgres -d postgres -v ON_ERROR_STOP=1 \
      -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
  fi
  echo "Ready: postgresql://$DB_USER@$PGHOST:$PGPORT/$DB_NAME"
}

ensure() {
  # Cron-safe: exits 0 silently when the server is already accepting
  # connections; otherwise starts it, retrying briefly (the '@reboot' run can
  # race with other boot-time work) and recording the outcome in autostart.log.
  if "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
    exit 0
  fi
  for attempt in 1 2 3 4 5; do
    if start >>"$CRONLOG" 2>&1; then
      echo "$(date -Is) PostgreSQL started (attempt $attempt)" >>"$CRONLOG"
      exit 0
    fi
    sleep $((attempt * 2))
  done
  echo "$(date -Is) ERROR: PostgreSQL failed to start after 5 attempts" >>"$CRONLOG"
  exit 1
}

case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop || true; start ;;
  ensure)  ensure ;;
  status)  "$PGBIN/pg_isready" -h "$PGHOST" -p "$PGPORT" ;;
  logs)    tail -n 50 -f "$LOGFILE" ;;
  init)    init ;;
  psql)    shift; PGPASSWORD="$DB_PASSWORD" "$PGBIN/psql" -h "$PGHOST" -p "$PGPORT" \
             -U "$DB_USER" -d "$DB_NAME" -P pager=off "$@" ;;
  *) echo "usage: $0 {start|stop|restart|ensure|status|logs|psql|init}" >&2; exit 2 ;;
esac
