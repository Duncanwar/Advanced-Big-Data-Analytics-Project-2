-- 2.2 Bulk-load the captured CSVs. Run from the project root:
--   psql -d momo -f sql/02_load.sql
-- Parents first: customers and devices, then accounts, account_devices, transfers.
\timing on
\echo '--- loading customers'
\copy customers FROM 'data/customers.csv' CSV HEADER
\echo '--- loading devices'
\copy devices FROM 'data/devices.csv' CSV HEADER
\echo '--- loading accounts'
\copy accounts FROM 'data/accounts.csv' CSV HEADER
\echo '--- loading account_devices'
\copy account_devices FROM 'data/account_devices.csv' CSV HEADER
\echo '--- loading transfers'
\copy transfers FROM 'data/transfers.csv' CSV HEADER
\timing off
