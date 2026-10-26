-- 2.2 Checks: row counts, roles, transfer audit totals, constraints, indexes, sizes.
--   psql -d momo -f sql/04_checks.sql
\pset footer off

\echo '=== row counts (expected 228000 / 248000 / 228600 / 285600 / 20003300)'
SELECT 'customers' AS table_name, count(*) AS rows FROM customers
UNION ALL SELECT 'accounts', count(*) FROM accounts
UNION ALL SELECT 'devices', count(*) FROM devices
UNION ALL SELECT 'account_devices', count(*) FROM account_devices
UNION ALL SELECT 'transfers', count(*) FROM transfers
UNION ALL SELECT 'TOTAL', (SELECT count(*) FROM customers) + (SELECT count(*) FROM accounts)
    + (SELECT count(*) FROM devices) + (SELECT count(*) FROM account_devices)
    + (SELECT count(*) FROM transfers);

\echo '=== account roles (expected person 240000, merchant 6000, agent 2000)'
SELECT role, count(*) AS accounts FROM accounts GROUP BY role ORDER BY accounts DESC;

\echo '=== transfer audit totals (compare with capture.py)'
SELECT count(*)                          AS transfer_count,
       min(occurred_at)                  AS earliest_occurred_at,
       to_timestamp(min(occurred_at))    AS earliest_cat,
       max(occurred_at)                  AS latest_occurred_at,
       to_timestamp(max(occurred_at))    AS latest_cat,
       sum(amount_rwf)                   AS sum_amount_rwf
FROM transfers;

\echo '=== constraints (convalidated = t means every existing row was checked)'
SELECT conrelid::regclass AS table_name, conname AS constraint_name,
       CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                    WHEN 'c' THEN 'CHECK' END AS type,
       convalidated, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, type, constraint_name;

\echo '=== NOT NULL columns'
SELECT table_name, count(*) AS columns,
       count(*) FILTER (WHERE is_nullable = 'NO') AS not_null_columns
FROM information_schema.columns
WHERE table_schema = 'public'
GROUP BY table_name ORDER BY table_name;

\echo '=== indexes'
SELECT tablename AS table_name, indexname AS index_name, indexdef AS definition
FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;

\echo '=== sizes (1 GB = 1,000,000,000 bytes)'
SELECT c.relname AS table_name,
       round(pg_table_size(c.oid) / 1e9, 3)          AS data_gb,
       round(pg_indexes_size(c.oid) / 1e9, 3)        AS index_gb,
       round(pg_total_relation_size(c.oid) / 1e9, 3) AS total_gb
FROM pg_class c
WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r'
UNION ALL
SELECT 'ALL TABLES',
       round(sum(pg_table_size(c.oid)) / 1e9, 3),
       round(sum(pg_indexes_size(c.oid)) / 1e9, 3),
       round(sum(pg_total_relation_size(c.oid)) / 1e9, 3)
FROM pg_class c
WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r'
ORDER BY total_gb;

\echo '=== whole database size'
SELECT current_database(), round(pg_database_size(current_database()) / 1e9, 3) AS database_gb;
