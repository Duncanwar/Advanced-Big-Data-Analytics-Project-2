#!/usr/bin/env bash
# Start/stop/status for the two project database services, so timing runs one service at a time.
#   tools/services.sh pg stop|start|status
#   tools/services.sh neo stop|start|status
# PostgreSQL runs from Postgres.app; it is restarted with the same options Postgres.app used
# (recorded in postmaster.opts), so the app keeps working as before.
set -euo pipefail
PGBIN=/Applications/Postgres.app/Contents/Versions/16/bin
PGDATA="$HOME/Library/Application Support/Postgres/var-16"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
NEO4J_HOME="${NEO4J_HOME:-$HOME/neo4j-mm/neo4j-community-5.26.0}"

case "$1:$2" in
  pg:stop)   "$PGBIN/pg_ctl" -D "$PGDATA" stop -m fast ;;
  pg:start)
    opts=$(sed -e 's/^[^ ]* "-D" "[^"]*" //' "$PGDATA/postmaster.opts")
    eval "\"$PGBIN/pg_ctl\" -D \"$PGDATA\" -l \"$PGDATA/postgresql.log\" -w start -o '$opts'" ;;
  pg:status) "$PGBIN/pg_ctl" -D "$PGDATA" status | head -1 ;;
  neo:stop)   "$NEO4J_HOME/bin/neo4j" stop ;;
  neo:start)
    "$NEO4J_HOME/bin/neo4j" start
    . "$(dirname "$0")/../.env"
    until "$NEO4J_HOME/bin/cypher-shell" -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1;" >/dev/null 2>&1; do sleep 2; done
    echo "Neo4j is ready" ;;
  neo:status) "$NEO4J_HOME/bin/neo4j" status ;;
  *) echo "usage: $0 pg|neo stop|start|status" >&2; exit 2 ;;
esac
