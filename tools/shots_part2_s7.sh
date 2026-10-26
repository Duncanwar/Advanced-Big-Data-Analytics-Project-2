#!/usr/bin/env bash
# Section 7 screenshots, 10 seconds apart. Each engine is load-tested with the other service stopped.
cd "$(dirname "$0")/.."
shot() { tools/shot.sh "$@"; sleep 10; }
active_pg() {   # a 16-client demonstration run (rep 0, excluded from results) while showing the clients
  (.venv/bin/python loadtest.py --engine pg --workload q4 --clients 16 --rep 0 >/dev/null 2>&1 &)
  shot 41_7-1_active_clients_pg "sleep 9; psql -d momo -c \"SELECT application_name, state, count(*) AS clients FROM pg_stat_activity WHERE application_name = 'loadtest' GROUP BY 1, 2\"; ps -o pid,%cpu,etime,command -p \$(pgrep -d, -f 'multiprocessing.spawn') | cut -c1-120"
  sleep 15
}
active_neo() {
  (.venv/bin/python loadtest.py --engine neo --workload q7 --clients 16 --rep 0 >/dev/null 2>&1 &)
  shot 43_7-1_active_clients_neo "sleep 9; \$NEO4J_HOME/bin/cypher-shell -u neo4j -p \"\$NEO4J_PASSWORD\" 'SHOW TRANSACTIONS YIELD transactionId, status, elapsedTime, currentQuery RETURN count(*) AS open_transactions, collect(DISTINCT status) AS states'; ps -o pid,%cpu,etime,command -p \$(pgrep -d, -f 'multiprocessing.spawn') | cut -c1-120"
  sleep 15
}
tools/services.sh neo stop >/dev/null
active_pg
shot 42_7-1_loadtest_pg 'tools/services.sh neo status; python loadtest.py --engine pg --all | tee outputs/7_loadtest_pg.txt'
tools/services.sh pg stop >/dev/null; tools/services.sh neo start >/dev/null
active_neo
shot 44_7-1_loadtest_neo 'tools/services.sh pg status; python loadtest.py --engine neo --all | tee outputs/7_loadtest_neo.txt'
tools/services.sh pg start >/dev/null
shot 45_7-1_7-2_summary 'python loadtest.py --summary | tee outputs/7_summary.txt'
NOFRONT=1 KEEP=1 tools/shot.sh 46_7-2_scaling_chart '(qlmanage -p outputs/loadtest_scaling.png >/dev/null 2>&1 &)' 3
pkill -f 'qlmanage -p outputs/loadtest_scaling.png'
