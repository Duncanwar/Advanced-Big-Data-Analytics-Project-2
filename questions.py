"""Parameterized SQL/Cypher pairs for the inspection trace (3.3) and Q1 to Q7."""
from datetime import datetime
from zoneinfo import ZoneInfo

KIGALI = ZoneInfo('Africa/Kigali')

SETS = {
    'A': (998, 24755, 6),
    'B': (147228, 186823, 13),
    'C': (206978, 6573, 8),
    'D': (237998, 21755, 6),
    'E': (144228, 183823, 13),
    'F': (203978, 3573, 8),
}


def review_hour(day):
    """Epoch seconds for 09:45:00 inclusive to 10:45:00 exclusive CAT on September `day`."""
    start = datetime(2026, 9, day, 9, 45, tzinfo=KIGALI)
    end = datetime(2026, 9, day, 10, 45, tzinfo=KIGALI)
    return int(start.timestamp()), int(end.timestamp())


def set_params(name):
    account, destination, day = SETS[name]
    start, end = review_hour(day)
    return dict(account=account, destination=destination, start=start, end=end)


# 3.3 Inspect one account: owner, one device and one outgoing transfer.
TRACE_SQL = """
SELECT a.account_id, a.role, c.customer_id, c.region,
       d.device_id, d.access_type, ad.first_day, ad.last_day, ad.observations,
       t.transfer_id, t.receiver_id, t.occurred_at, t.amount_rwf
FROM accounts a
JOIN customers c        ON c.customer_id = a.customer_id
JOIN account_devices ad ON ad.account_id = a.account_id
JOIN devices d          ON d.device_id = ad.device_id
JOIN transfers t        ON t.sender_id = a.account_id
WHERE a.account_id = %(account)s
ORDER BY d.device_id, t.transfer_id
LIMIT 1
"""
TRACE_CYPHER = """
MATCH (c:Customer)-[:OWNS]->(a:Account {account_id: $account})-[u:USED_DEVICE]->(d:Device),
      (a)-[t:TRANSFER]->(r:Account)
RETURN a.account_id, a.role, c.customer_id, c.region,
       d.device_id, d.access_type, u.first_day, u.last_day, u.observations,
       t.transfer_id, r.account_id, t.occurred_at, t.amount_rwf
ORDER BY d.device_id, t.transfer_id
LIMIT 1
"""

REPEATS_SQL = """
SELECT receiver_id, count(*) AS transfers, sum(amount_rwf) AS total_rwf,
       min(occurred_at) AS first_at, max(occurred_at) AS last_at
FROM transfers WHERE sender_id = %(account)s
GROUP BY receiver_id HAVING count(*) > 1
ORDER BY transfers DESC, receiver_id
"""
REPEATS_CYPHER = """
MATCH (:Account {account_id: $account})-[t:TRANSFER]->(r:Account)
WITH r.account_id AS receiver_id, count(t) AS transfers, sum(t.amount_rwf) AS total_rwf,
     min(t.occurred_at) AS first_at, max(t.occurred_at) AS last_at
WHERE transfers > 1
RETURN receiver_id, transfers, total_rwf, first_at, last_at
ORDER BY transfers DESC, receiver_id
"""
PAIRS_SQL = """
SELECT count(*) AS transfers,
       (SELECT count(*) FROM (SELECT DISTINCT sender_id, receiver_id FROM transfers) p) AS distinct_pairs
FROM transfers
"""

# Q1 Account activity in the review hour, all receiver roles, zeros when nothing matches.
Q1_SQL = """
SELECT COUNT(*), COALESCE(SUM(amount_rwf), 0)
FROM transfers WHERE sender_id = %(account)s
  AND occurred_at >= %(start)s AND occurred_at < %(end)s
"""
Q1_CYPHER = """
MATCH (a:Account {account_id: $account})-[t:TRANSFER]->()
WHERE t.occurred_at >= $start AND t.occurred_at < $end
RETURN count(t), coalesce(sum(t.amount_rwf), 0)
"""

# Q2 Daily activity over the whole month, grouped into CAT days.
Q2_SQL = """
SELECT (to_timestamp(occurred_at) AT TIME ZONE 'Africa/Kigali')::date AS day,
       COUNT(*) AS transfers, SUM(amount_rwf) AS total_rwf
FROM transfers
GROUP BY day
ORDER BY day
"""
Q2_CYPHER = """
MATCH ()-[t:TRANSFER]->()
WITH date(datetime({epochSeconds: t.occurred_at, timezone: 'Africa/Kigali'})) AS day, t.amount_rwf AS amount
RETURN day, count(*) AS transfers, sum(amount) AS total_rwf
ORDER BY day
"""

# Q3 Other accounts observed on the same device during overlapping day intervals.
Q3_SQL = """
SELECT o.account_id AS other_account, o.device_id, d.access_type,
       GREATEST(r.first_day, o.first_day) AS overlap_start,
       LEAST(r.last_day, o.last_day) AS overlap_end
FROM account_devices r
JOIN account_devices o ON o.device_id = r.device_id AND o.account_id <> r.account_id
JOIN devices d ON d.device_id = r.device_id
WHERE r.account_id = %(account)s
  AND GREATEST(r.first_day, o.first_day) <= LEAST(r.last_day, o.last_day)
ORDER BY other_account, o.device_id
"""
Q3_CYPHER = """
MATCH (a:Account {account_id: $account})-[r:USED_DEVICE]->(d:Device)<-[o:USED_DEVICE]-(b:Account)
WHERE b.account_id <> $account
WITH b, d,
     CASE WHEN r.first_day > o.first_day THEN r.first_day ELSE o.first_day END AS overlap_start,
     CASE WHEN r.last_day < o.last_day THEN r.last_day ELSE o.last_day END AS overlap_end
WHERE overlap_start <= overlap_end
RETURN b.account_id AS other_account, d.device_id, d.access_type, overlap_start, overlap_end
ORDER BY other_account, d.device_id
"""

# Q4 Ownership and device network: distinct other accounts within `depth` OWNS/USED_DEVICE links,
Q4_SQL = """
WITH RECURSIVE edges(sk, si, dk, di) AS (
    SELECT 'Customer'::text, customer_id, 'Account'::text, account_id FROM accounts
    UNION ALL
    SELECT 'Account', account_id, 'Customer', customer_id FROM accounts
    UNION ALL
    SELECT 'Account', account_id, 'Device', device_id FROM account_devices
    UNION ALL
    SELECT 'Device', device_id, 'Account', account_id FROM account_devices
), walk(kind, id, depth) AS (
    SELECT 'Account'::text, %(account)s::integer, 0
    UNION
    SELECT e.dk, e.di, w.depth + 1
    FROM walk w JOIN edges e ON e.sk = w.kind AND e.si = w.id
    WHERE w.depth < %(depth)s
)
SELECT c.region, COUNT(DISTINCT w.id) AS accounts
FROM walk w
JOIN accounts a ON a.account_id = w.id
JOIN customers c ON c.customer_id = a.customer_id
WHERE w.kind = 'Account' AND w.id <> %(account)s
GROUP BY c.region
ORDER BY c.region
"""
Q4_CYPHER = """
MATCH (a:Account {{account_id: $account}})
MATCH (a)-[:OWNS|USED_DEVICE*1..{depth}]-(b:Account)
WHERE b <> a
WITH DISTINCT b
MATCH (c:Customer)-[:OWNS]->(b)
RETURN c.region AS region, count(b) AS accounts
ORDER BY region
"""


def q4_cypher(depth):
    return Q4_CYPHER.format(depth=int(depth))


Q4_PATH_CYPHER = """
MATCH (a:Account {account_id: $account}), (b:Account {account_id: $target})
MATCH p = shortestPath((a)-[:OWNS|USED_DEVICE*..10]-(b))
RETURN [n IN nodes(p) | labels(n)[0] + ' ' + toString(coalesce(n.account_id, n.customer_id, n.device_id))] AS path,
       length(p) AS links
"""
Q4_FARTHEST_SQL = Q4_SQL.split('SELECT c.region')[0] + """
SELECT w.id, MIN(w.depth) AS depth
FROM walk w
WHERE w.kind = 'Account' AND w.id <> %(account)s
GROUP BY w.id
ORDER BY depth DESC, w.id
LIMIT 1
"""

# Q5 Rapid onward payments: exactly three directed transfers through four distinct accounts.
Q5_SQL = """
SELECT t1.transfer_id, t2.transfer_id, t3.transfer_id, t3.receiver_id
FROM transfers t1
JOIN transfers t2 ON t2.sender_id = t1.receiver_id
                 AND t2.occurred_at > t1.occurred_at AND t2.occurred_at <= t1.occurred_at + 600
JOIN transfers t3 ON t3.sender_id = t2.receiver_id
                 AND t3.occurred_at > t2.occurred_at AND t3.occurred_at <= t2.occurred_at + 600
WHERE t1.sender_id = %(account)s
  AND t1.occurred_at >= %(start)s AND t1.occurred_at < %(end)s
  AND 90::bigint * t1.amount_rwf <= 100::bigint * t2.amount_rwf
  AND 100::bigint * t2.amount_rwf <= 105::bigint * t1.amount_rwf
  AND 90::bigint * t2.amount_rwf <= 100::bigint * t3.amount_rwf
  AND 100::bigint * t3.amount_rwf <= 105::bigint * t2.amount_rwf
  AND t1.sender_id <> t1.receiver_id AND t1.sender_id <> t2.receiver_id AND t1.sender_id <> t3.receiver_id
  AND t1.receiver_id <> t2.receiver_id AND t1.receiver_id <> t3.receiver_id
  AND t2.receiver_id <> t3.receiver_id
ORDER BY 1, 2, 3, 4
"""
Q5_CYPHER = """
MATCH (a:Account {account_id: $account})-[t1:TRANSFER]->(b:Account)-[t2:TRANSFER]->(c:Account)-[t3:TRANSFER]->(d:Account)
WHERE $start <= t1.occurred_at < $end
  AND t1.occurred_at < t2.occurred_at <= t1.occurred_at + 600
  AND t2.occurred_at < t3.occurred_at <= t2.occurred_at + 600
  AND 90 * t1.amount_rwf <= 100 * t2.amount_rwf <= 105 * t1.amount_rwf
  AND 90 * t2.amount_rwf <= 100 * t3.amount_rwf <= 105 * t2.amount_rwf
  AND a <> b AND a <> c AND a <> d AND b <> c AND b <> d AND c <> d
RETURN t1.transfer_id, t2.transfer_id, t3.transfer_id, d.account_id
ORDER BY t1.transfer_id, t2.transfer_id, t3.transfer_id, d.account_id
"""

# Q6 Circular payments: 3 to 8 transfers from and back to the review account, all in its hour,
Q6_SQL = """
WITH RECURSIVE walk(account, ids, first_at, last_at, last_amount, len) AS (
    SELECT receiver_id, ARRAY[transfer_id], occurred_at, occurred_at, amount_rwf, 1
    FROM transfers
    WHERE sender_id = %(account)s AND occurred_at >= %(start)s AND occurred_at < %(end)s
    UNION ALL
    SELECT t.receiver_id, w.ids || t.transfer_id, w.first_at, t.occurred_at, t.amount_rwf, w.len + 1
    FROM walk w
    JOIN transfers t ON t.sender_id = w.account
    WHERE w.account <> %(account)s
      AND w.len < 8
      AND t.occurred_at > w.last_at AND t.occurred_at < %(end)s
      AND t.occurred_at <= w.first_at + 1800
      AND 90::bigint * w.last_amount <= 100::bigint * t.amount_rwf
      AND 100::bigint * t.amount_rwf <= 105::bigint * w.last_amount
)
SELECT ids, len FROM walk
WHERE account = %(account)s AND len >= 3
ORDER BY ids
"""
Q6_CYPHER = """
MATCH (a:Account {account_id: $account})
MATCH p = (a)(()-[t:TRANSFER WHERE $start <= t.occurred_at < $end]->()){3,8}(a)
WHERE all(i IN range(0, size(t) - 2) WHERE t[i].occurred_at < t[i + 1].occurred_at
          AND 90 * t[i].amount_rwf <= 100 * t[i + 1].amount_rwf <= 105 * t[i].amount_rwf)
  AND t[-1].occurred_at - t[0].occurred_at <= 1800
  AND none(n IN nodes(p)[1..-1] WHERE n = a)
RETURN [x IN t | x.transfer_id] AS ids, size(t) AS len
ORDER BY ids
"""
TRANSFER_DETAILS_SQL = """
SELECT transfer_id, sender_id, receiver_id, occurred_at,
       to_char(to_timestamp(occurred_at), 'YYYY-MM-DD HH24:MI:SS') AS cat_time, amount_rwf
FROM transfers WHERE transfer_id = ANY(%(ids)s)
ORDER BY occurred_at
"""

# Q7 Shortest transfer connection: fewest directed transfers from review account to destination,
Q7_SQL = """
WITH RECURSIVE walk(account, depth) AS (
    SELECT account_id, 0 FROM accounts
    WHERE account_id = %(account)s AND role = 'person'
    UNION
    SELECT t.receiver_id, w.depth + 1
    FROM walk w
    JOIN transfers t ON t.sender_id = w.account
    JOIN accounts r ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE w.depth < %(bound)s AND w.account <> %(destination)s
)
SELECT MIN(depth) AS length FROM walk WHERE account = %(destination)s
"""
Q7_CYPHER = """
MATCH (a:Account {{account_id: $account, role: 'person'}}), (b:Account {{account_id: $destination, role: 'person'}})
OPTIONAL MATCH p = SHORTEST 1 (a)(()-[:TRANSFER]->(n:Account WHERE n.role = 'person')){{1,{bound}}}(b)
RETURN length(p) AS length
"""
Q7_PATH_CYPHER = """
MATCH (a:Account {{account_id: $account, role: 'person'}}), (b:Account {{account_id: $destination, role: 'person'}})
MATCH p = SHORTEST 1 (a)(()-[:TRANSFER]->(n:Account WHERE n.role = 'person')){{1,{bound}}}(b)
RETURN [n IN nodes(p) | n.account_id] AS accounts, [r IN relationships(p) | r.transfer_id] AS transfers
"""


def q7_cypher(bound):
    return Q7_CYPHER.format(bound=int(bound))


def q7_path_cypher(bound):
    return Q7_PATH_CYPHER.format(bound=int(bound))


Q7_PATH_CHECK_SQL = """
SELECT h.step, t.transfer_id, t.sender_id, t.receiver_id, s.role, r.role,
       t.sender_id = (%(accounts)s::int[])[h.step] AND t.receiver_id = (%(accounts)s::int[])[h.step + 1] AS links_in_order
FROM unnest(%(transfers)s::bigint[]) WITH ORDINALITY AS h(transfer_id, step)
LEFT JOIN transfers t ON t.transfer_id = h.transfer_id
LEFT JOIN accounts s ON s.account_id = t.sender_id
LEFT JOIN accounts r ON r.account_id = t.receiver_id
ORDER BY h.step
"""

# 6.3 SQL improvement for Q7: search from both ends. The forward walk goes ceil(bound/2) steps from
Q7_SQL_BIDIRECTIONAL = """
WITH RECURSIVE fwd(account, depth) AS (
    SELECT account_id, 0 FROM accounts
    WHERE account_id = %(account)s AND role = 'person'
    UNION
    SELECT t.receiver_id, f.depth + 1
    FROM fwd f
    JOIN transfers t ON t.sender_id = f.account
    JOIN accounts r ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE f.depth < %(forward_steps)s
), bwd(account, depth) AS (
    SELECT account_id, 0 FROM accounts
    WHERE account_id = %(destination)s AND role = 'person'
    UNION
    SELECT t.sender_id, b.depth + 1
    FROM bwd b
    JOIN transfers t ON t.receiver_id = b.account
    JOIN accounts s ON s.account_id = t.sender_id AND s.role = 'person'
    WHERE b.depth < %(backward_steps)s
), f AS (
    SELECT account, MIN(depth) AS depth FROM fwd GROUP BY account
), b AS (
    SELECT account, MIN(depth) AS depth FROM bwd GROUP BY account
)
SELECT MIN(f.depth + b.depth) AS length
FROM f JOIN b USING (account)
WHERE f.depth + b.depth <= %(bound)s
"""


def q7_params(params, bound):
    """Parameters for the Q7 SQL versions: the bound and its forward/backward split."""
    return dict(params, bound=bound, forward_steps=(bound + 1) // 2, backward_steps=bound // 2)
