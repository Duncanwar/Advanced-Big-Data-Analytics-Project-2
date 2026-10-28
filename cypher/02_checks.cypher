// 3.2 Checks: counts, roles, ownership, unique transfer_id and audit totals.

MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
MATCH (n) RETURN count(n) AS total_nodes;

MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS relationships ORDER BY type;
MATCH ()-[r]->() RETURN count(r) AS total_relationships;

MATCH (a:Account) RETURN a.role AS role, count(*) AS accounts ORDER BY accounts DESC;

MATCH (a:Account)
WITH COUNT { (:Customer)-[:OWNS]->(a) } AS owners
RETURN owners, count(*) AS accounts ORDER BY owners;

MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfers, count(DISTINCT t.transfer_id) AS distinct_transfer_ids,
       min(t.transfer_id) AS min_id, max(t.transfer_id) AS max_id;

MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfer_count, min(t.occurred_at) AS earliest_occurred_at,
       max(t.occurred_at) AS latest_occurred_at, sum(t.amount_rwf) AS sum_amount_rwf;
