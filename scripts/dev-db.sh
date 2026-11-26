#!/usr/bin/env bash
# Local development database (plain PostgreSQL, no Docker or Supabase account needed).
#
#   scripts/dev-db.sh start    start the project-local server on port 54329
#   scripts/dev-db.sh reset    drop and recreate the civictexas database and apply migrations
#   scripts/dev-db.sh stop     stop the server
#
# Data lives in .local/pgdata (git-ignored).
set -euo pipefail
cd "$(dirname "$0")/.."

PGBIN="${PGBIN:-$(brew --prefix postgresql@16 2>/dev/null)/bin}"
export PATH="$PGBIN:$PATH"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
PORT=54329
DATA=.local/pgdata
PSQL=(psql -h localhost -p "$PORT" -U postgres -v ON_ERROR_STOP=1 -q)

case "${1:-}" in
  start)
    if [ ! -d "$DATA" ]; then
      mkdir -p .local
      initdb -D "$DATA" -U postgres --auth=trust -E UTF8 --locale=C >/dev/null
    fi
    pg_ctl -D "$DATA" -o "-p $PORT -k /tmp" -l .local/postgres.log -w status >/dev/null 2>&1 \
      || pg_ctl -D "$DATA" -o "-p $PORT -k /tmp" -l .local/postgres.log -w start
    ;;
  reset)
    "${PSQL[@]}" -d postgres -c "drop database if exists civictexas with (force)" -c "create database civictexas"
    "${PSQL[@]}" -d civictexas -f supabase/local/supabase_shim.sql
    for migration in supabase/migrations/*.sql; do
      echo "applying $migration"
      "${PSQL[@]}" -d civictexas -f "$migration"
    done
    ;;
  stop)
    pg_ctl -D "$DATA" -w stop
    ;;
  *)
    echo "usage: $0 {start|reset|stop}" >&2
    exit 2
    ;;
esac
