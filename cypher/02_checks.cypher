// 3.2 Checks: counts, roles, ownership, unique transfer_id and audit totals.
//   cypher-shell -u neo4j -p <password> -f cypher/02_checks.cypher

// Node counts (expected Customer 228000, Account 248000, Device 228600; total 704600)
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
MATCH (n) RETURN count(n) AS total_nodes;

// Relationship counts (expected OWNS 248000, USED_DEVICE 285600, TRANSFER 20003300; total 20536900)
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS relationships ORDER BY type;
MATCH ()-[r]->() RETURN count(r) AS total_relationships;

// Account roles (expected person 240000, merchant 6000, agent 2000)
MATCH (a:Account) RETURN a.role AS role, count(*) AS accounts ORDER BY accounts DESC;

// Exactly one owner per account (expected 248000 accounts with 1 owner, 0 otherwise)
MATCH (a:Account)
WITH COUNT { (:Customer)-[:OWNS]->(a) } AS owners
RETURN owners, count(*) AS accounts ORDER BY owners;

// Unique transfer_id (expected distinct = count = 20003300, ids 1..20003300)
MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfers, count(DISTINCT t.transfer_id) AS distinct_transfer_ids,
       min(t.transfer_id) AS min_id, max(t.transfer_id) AS max_id;

// Capture audit totals (expected 20003300, 1788235200, 1790798399, 231482327870)
MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfer_count, min(t.occurred_at) AS earliest_occurred_at,
       max(t.occurred_at) AS latest_occurred_at, sum(t.amount_rwf) AS sum_amount_rwf;
