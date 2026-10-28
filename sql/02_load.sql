-- 2.2 Bulk-load the captured CSVs (run from the project root).
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
