#!/usr/bin/env bash
# 3.2 Rebuild the Neo4j graph end to end: typed import copies, offline full import,
# constraints/index, checks, then remove the temporary copies.
#   ./neo4j_import.sh
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}"
NEO4J_HOME="${NEO4J_HOME:-$HOME/neo4j-mm/neo4j-community-5.26.0}"
CS=("$NEO4J_HOME/bin/cypher-shell" -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" --format plain)

.venv/bin/python prepare_import.py | tee outputs/3_2_prepare_import.txt

"$NEO4J_HOME/bin/neo4j" stop || true
"$NEO4J_HOME/bin/neo4j" status || true
start=$(date +%s)
"$NEO4J_HOME/bin/neo4j-admin" database import full neo4j --overwrite-destination --id-type=integer \
  --report-file=outputs/3_2_import.report \
  --nodes=Customer=import/customers.csv --nodes=Account=import/accounts.csv --nodes=Device=import/devices.csv \
  --relationships=OWNS=import/owns.csv --relationships=USED_DEVICE=import/used_device.csv \
  --relationships=TRANSFER=import/transfers.csv | tee outputs/3_2_import.txt
echo "IMPORT_WALL_SECONDS=$(( $(date +%s) - start ))" | tee -a outputs/3_2_import.txt

"$NEO4J_HOME/bin/neo4j" start
until "${CS[@]}" "RETURN 1;" >/dev/null 2>&1; do sleep 2; done

start=$(date +%s)
"${CS[@]}" -f cypher/01_constraints_indexes.cypher | tee outputs/3_2_constraints_indexes.txt
echo "SETUP_WALL_SECONDS=$(( $(date +%s) - start ))" | tee -a outputs/3_2_constraints_indexes.txt

"${CS[@]}" -f cypher/02_checks.cypher | tee outputs/3_2_checks.txt
DATA="$NEO4J_HOME/data"
python3 - "$DATA" <<'EOF' | tee -a outputs/3_2_checks.txt
import sys
from pathlib import Path
data = Path(sys.argv[1])
size = lambda p: sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
print(f"store GB (10^9 bytes): {size(data / 'databases' / 'neo4j') / 1e9:.3f}")
print(f"transaction log GB:    {size(data / 'transactions' / 'neo4j') / 1e9:.6f}")
EOF

rm -r import
echo "temporary import copies removed"
