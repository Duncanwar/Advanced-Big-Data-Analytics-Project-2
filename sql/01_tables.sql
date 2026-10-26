-- 2.1 Define the five tables.
-- Column types, NOT NULL and CHECK rules are created here, before loading.
-- Primary keys, foreign keys and indexes are added after the bulk load in
-- 03_constraints_indexes.sql so their setup time can be recorded separately.

DROP TABLE IF EXISTS transfers, account_devices, accounts, devices, customers CASCADE;

CREATE TABLE customers (
    customer_id INTEGER NOT NULL,          -- customer (person or business) identifier
    region      TEXT    NOT NULL           -- Rwandan province / Kigali
);

CREATE TABLE accounts (
    account_id  INTEGER NOT NULL,          -- wallet identifier
    customer_id INTEGER NOT NULL,          -- owning customer
    role        TEXT    NOT NULL           -- person | merchant | agent
);

CREATE TABLE devices (
    device_id   INTEGER NOT NULL,          -- device identifier
    access_type TEXT    NOT NULL           -- handset | public_terminal
);

CREATE TABLE account_devices (
    account_id   INTEGER  NOT NULL,        -- wallet observed on the device
    device_id    INTEGER  NOT NULL,        -- device observed
    first_day    SMALLINT NOT NULL,        -- first observation day, 0 = 1 Sep (inclusive)
    last_day     SMALLINT NOT NULL,        -- last observation day, 29 = 30 Sep (inclusive)
    observations INTEGER  NOT NULL,        -- number of observations within the interval
    CONSTRAINT account_devices_observations_positive CHECK (observations > 0),
    CONSTRAINT account_devices_day_range CHECK (0 <= first_day AND first_day <= last_day AND last_day <= 29)
);

CREATE TABLE transfers (
    transfer_id BIGINT  NOT NULL,          -- event identifier
    sender_id   INTEGER NOT NULL,          -- paying wallet
    receiver_id INTEGER NOT NULL,          -- receiving wallet
    occurred_at BIGINT  NOT NULL,          -- Unix seconds (UTC epoch)
    amount_rwf  INTEGER NOT NULL,          -- whole Rwandan francs
    CONSTRAINT transfers_amount_positive CHECK (amount_rwf > 0)
);
