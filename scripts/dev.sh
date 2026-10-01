#!/usr/bin/env bash
#
# Manage the local Maims dev stack: PostgreSQL + Django backend + Vite frontend.
#
#   ./scripts/dev.sh start     bring the whole stack up (idempotent)
#   ./scripts/dev.sh stop      stop backend + frontend (PostgreSQL keeps running)
#   ./scripts/dev.sh restart   stop then start
#   ./scripts/dev.sh status    what is up right now?
#   ./scripts/dev.sh logs      tail the backend and frontend logs
#
# Logs live in /tmp/maims-dev (override the directory with RUNDIR=...).
# The frontend dev server proxies /api/v1 and /media to the backend, so BOTH
# must be running for the site to show dynamic data.
set -euo pipefail

PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PATH

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO/maims-project/backend"
FRONTEND="$REPO/frontend"
RUNDIR="${RUNDIR:-/tmp/maims-dev}"
BACKEND_LOG="$RUNDIR/backend.log"
FRONTEND_LOG="$RUNDIR/frontend.log"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
mkdir -p "$RUNDIR"

PY="$BACKEND/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

port_up() {
  (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -q ":$1 "
}

start() {
  "$REPO/scripts/pg.sh" ensure

  if port_up "$BACKEND_PORT"; then
    echo "backend   : already up on $BACKEND_PORT"
  else
    (cd "$BACKEND" && nohup "$PY" manage.py runserver "0.0.0.0:$BACKEND_PORT" \
      >>"$BACKEND_LOG" 2>&1 &)
    echo "backend   : starting on $BACKEND_PORT (log: $BACKEND_LOG)"
  fi

  if port_up "$FRONTEND_PORT"; then
    echo "frontend  : already up on $FRONTEND_PORT"
  else
    if ! command -v npm >/dev/null 2>&1; then
      echo "frontend  : SKIPPED - npm not found on PATH" >&2
    else
      (cd "$FRONTEND" && nohup npm run dev >>"$FRONTEND_LOG" 2>&1 &)
      echo "frontend  : starting on $FRONTEND_PORT (log: $FRONTEND_LOG)"
    fi
  fi
}

stop() {
  pkill -f 'manage.py runserver' && echo "backend   : stopped" || echo "backend   : was not running"
  pkill -f 'npm run dev' 2>/dev/null || true
  pkill -f 'node_modules/vite' 2>/dev/null || true
  echo "frontend  : stopped (if it was running)"
}

status() {
  "$REPO/scripts/pg.sh" status || true
  if port_up "$BACKEND_PORT";  then echo "backend   : UP on $BACKEND_PORT";  else echo "backend   : DOWN";  fi
  if port_up "$FRONTEND_PORT"; then echo "frontend  : UP on $FRONTEND_PORT"; else echo "frontend  : DOWN"; fi
}

case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop || true; sleep 2; start ;;
  status)  status ;;
  logs)    tail -n 40 "$BACKEND_LOG" "$FRONTEND_LOG" ;;
  *) echo "usage: $0 {start|stop|restart|status|logs}" >&2; exit 2 ;;
esac
