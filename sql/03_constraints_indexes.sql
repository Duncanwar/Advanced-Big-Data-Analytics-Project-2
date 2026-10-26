-- 2.1 keys and 2.2 indexes, applied after the bulk load and timed separately.
--   psql -d momo -f sql/03_constraints_indexes.sql
SET maintenance_work_mem = '512MB';
\timing on

\echo '--- primary keys'
ALTER TABLE customers       ADD CONSTRAINT customers_pkey       PRIMARY KEY (customer_id);
ALTER TABLE devices         ADD CONSTRAINT devices_pkey         PRIMARY KEY (device_id);
ALTER TABLE accounts        ADD CONSTRAINT accounts_pkey        PRIMARY KEY (account_id);
ALTER TABLE account_devices ADD CONSTRAINT account_devices_pkey PRIMARY KEY (account_id, device_id);
ALTER TABLE transfers       ADD CONSTRAINT transfers_pkey       PRIMARY KEY (transfer_id);

\echo '--- foreign keys: ownership, device use, both transfer endpoints'
ALTER TABLE accounts        ADD CONSTRAINT accounts_customer_fk        FOREIGN KEY (customer_id) REFERENCES customers;
ALTER TABLE account_devices ADD CONSTRAINT account_devices_account_fk  FOREIGN KEY (account_id)  REFERENCES accounts;
ALTER TABLE account_devices ADD CONSTRAINT account_devices_device_fk   FOREIGN KEY (device_id)   REFERENCES devices;
ALTER TABLE transfers       ADD CONSTRAINT transfers_sender_fk         FOREIGN KEY (sender_id)   REFERENCES accounts;
ALTER TABLE transfers       ADD CONSTRAINT transfers_receiver_fk       FOREIGN KEY (receiver_id) REFERENCES accounts;

\echo '--- secondary indexes'
CREATE INDEX accounts_customer_account_idx ON accounts (customer_id, account_id);
CREATE INDEX account_devices_device_account_idx ON account_devices (device_id, account_id);
CREATE INDEX transfers_sender_time_idx ON transfers (sender_id, occurred_at)
    INCLUDE (receiver_id, amount_rwf, transfer_id);
CREATE INDEX transfers_receiver_time_idx ON transfers (receiver_id, occurred_at)
    INCLUDE (sender_id, amount_rwf, transfer_id);
CREATE INDEX transfers_occurred_brin ON transfers USING brin (occurred_at);

\echo '--- analyze'
ANALYZE;
\timing off
