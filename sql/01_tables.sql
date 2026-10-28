-- 2.1 Define the five tables.

DROP TABLE IF EXISTS transfers, account_devices, accounts, devices, customers CASCADE;

CREATE TABLE customers (
    customer_id INTEGER NOT NULL,
    region      TEXT    NOT NULL
);

CREATE TABLE accounts (
    account_id  INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    role        TEXT    NOT NULL
);

CREATE TABLE devices (
    device_id   INTEGER NOT NULL,
    access_type TEXT    NOT NULL
);

CREATE TABLE account_devices (
    account_id   INTEGER  NOT NULL,
    device_id    INTEGER  NOT NULL,
    first_day    SMALLINT NOT NULL,
    last_day     SMALLINT NOT NULL,
    observations INTEGER  NOT NULL,
    CONSTRAINT account_devices_observations_positive CHECK (observations > 0),
    CONSTRAINT account_devices_day_range CHECK (0 <= first_day AND first_day <= last_day AND last_day <= 29)
);

CREATE TABLE transfers (
    transfer_id BIGINT  NOT NULL,
    sender_id   INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    occurred_at BIGINT  NOT NULL,
    amount_rwf  INTEGER NOT NULL,
    CONSTRAINT transfers_amount_positive CHECK (amount_rwf > 0)
);
