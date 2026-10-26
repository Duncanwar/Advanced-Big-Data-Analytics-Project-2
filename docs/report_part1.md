# Project 2 report notes: Sections 1 to 4 (pages 1 to 4 of the brief)

All numbers below come from the files in `outputs/`. The screenshots the brief asks for are listed in
`docs/screenshots_part1.md` (with the command that produces each one).

---

## 1 Capture the data

### 1.1 Prepare your workspace

| Item | Value |
|---|---|
| CPU | Apple M2, 8 cores |
| RAM | 8.6 GB (8 GiB) |
| OS | macOS 14.6.1 (arm64) |
| PostgreSQL | 16.8 (Postgres.app), database `momo`, `TimeZone = Africa/Kigali` (set with `ALTER DATABASE momo SET timezone`) |
| PostgreSQL memory | `shared_buffers 128MB`, `work_mem 4MB`, `maintenance_work_mem 64MB` (512MB for the index build session), `effective_cache_size 4GB`, `max_parallel_workers_per_gather 2` |
| Neo4j | 5.26.0 **Community**, dedicated instance, default `neo4j` database, Java 17 (OpenJDK 17.0.14) |
| Neo4j memory | heap initial/max 2 GiB, page cache 2 GiB |
| Python and drivers | Python 3.13.2, psycopg 3.3.6, neo4j driver 6.4.1, numpy 2.5.4, matplotlib 3.11.2 |
| Generator | unchanged, sha256 `2ea0e59d…e9455a` |

Source: `outputs/1_1_workspace.txt` (from `workspace_info.py`, which also proves both connections).

### 1.2 Build capture.py

`capture.py` imports the generator as `g`, prints `g.dataset_info()` and `g.FIELDS`, and previews ten
records from each `iter_<stream>()` with `itertools.islice`. Because each call to `iter_<stream>()`
creates a fresh generator, the preview doesn't consume rows from the capture. Each stream is then written
row by row with `csv.DictWriter`, so the full stream is never held in memory. The script logs every
million transfers and keeps running audit totals.

| Stream | Consumed | Written | Expected | Match | Seconds | CSV MB |
|---|---:|---:|---:|---|---:|---:|
| customers | 228,000 | 228,000 | 228,000 | yes | 0.4 | 3.6 |
| accounts | 248,000 | 248,000 | 248,000 | yes | 0.5 | 5.2 |
| devices | 228,600 | 228,600 | 228,600 | yes | 0.3 | 3.6 |
| account_devices | 285,600 | 285,600 | 285,600 | yes | 0.7 | 6.3 |
| transfers | 20,003,300 | 20,003,300 | 20,003,300 | yes | 70.6 | 780.2 |
| **Total** | **20,993,500** | **20,993,500** | **20,993,500** | **yes** | **72.4** | **798.8** |

**Transfer audit totals:**

| Audit item | Value |
|---|---|
| Transfer count | 20,003,300 |
| Earliest `occurred_at` | 1788235200 (2026-09-01 06:00:00 CAT) |
| Latest `occurred_at` | 1790798399 (2026-09-30 21:59:59 CAT) |
| Sum of `amount_rwf` | 231,482,327,870 RWF |

Earliest and latest are tracked with explicit min/max checks because transfers aren't time-sorted.

---

## 2 Build PostgreSQL

### 2.1 Define the five tables

```
 customers                      accounts                         devices
 ─────────────────────          ──────────────────────           ─────────────────────
 PK customer_id  INTEGER ◄──┐   PK account_id   INTEGER ◄──┐     PK device_id    INTEGER ◄──┐
    region       TEXT       └── FK customer_id  INTEGER    │        access_type  TEXT       │
                                   role         TEXT       │                                │
                                                           │                                │
 transfers                                                 │   account_devices              │
 ─────────────────────────────                             │   ─────────────────────────────│
 PK transfer_id  BIGINT                                    ├── PK,FK account_id  INTEGER    │
 FK sender_id    INTEGER ──────────────────────────────────┤   PK,FK device_id   INTEGER ───┘
 FK receiver_id  INTEGER ──────────────────────────────────┘         first_day   SMALLINT
    occurred_at  BIGINT                                              last_day    SMALLINT
    amount_rwf   INTEGER                                             observations INTEGER
```

| Table.field | Meaning and unit |
|---|---|
| customers.customer_id | Customer identifier (integer) |
| customers.region | Kigali, Northern, Southern, Eastern or Western |
| accounts.account_id | Wallet identifier (integer) |
| accounts.customer_id | Owning customer (FK, ownership) |
| accounts.role | `person` (240,000), `merchant` (6,000) or `agent` (2,000) |
| devices.device_id | Device identifier (integer) |
| devices.access_type | `handset` or `public_terminal` |
| account_devices.first_day / last_day | Inclusive observation interval, as day numbers 0 to 29 (day 0 = 1 Sep 2026 CAT) |
| account_devices.observations | Number of observations of that wallet on that device within the interval. This is observed use, not ownership. |
| transfers.transfer_id | Event identifier |
| transfers.sender_id / receiver_id | Paying and receiving wallets (FKs, both endpoints) |
| transfers.occurred_at | Unix epoch seconds. CAT = UTC+2; `to_timestamp()` shows it in Africa/Kigali time. |
| transfers.amount_rwf | Positive whole Rwandan francs |

**Constraints:**

- Every column is `NOT NULL`.
- Primary keys are the entity/event IDs, plus `(account_id, device_id)` for `account_devices`.
- Five foreign keys: ownership, device use (account and device), and both transfer endpoints.
- `CHECK` constraints: `amount_rwf > 0`, `observations > 0`, and `0 <= first_day <= last_day <= 29`.
- Definitions are in `sql/01_tables.sql` and `sql/03_constraints_indexes.sql`.

### 2.2 Bulk-load and check

Load order: customers, devices, accounts, account_devices, transfers (`\copy … CSV HEADER`, `sql/02_load.sql`).
Keys and indexes were added **after** loading, so that each index is built once rather than maintained
row by row, and so their setup time could be measured separately.

| Step | Seconds |
|---|---:|
| Load customers / devices / accounts / account_devices | 0.134 / 0.117 / 0.164 / 0.195 |
| Load transfers | 18.961 |
| **Total loading** | **19.57** |
| Primary keys (transfers: 28.51) | 29.23 |
| Foreign keys (two transfer FKs: 3.44 + 3.42) | 7.11 |
| Secondary indexes (two covering transfer indexes: 27.83 + 30.24, BRIN 2.57) | 60.84 |
| ANALYZE | 1.08 |
| **Total index/constraint setup** | **98.25** |

These are the timings from the screenshot run (screenshots 06 and 07). An earlier identical run took
17.65 s to load and 111.38 s for setup.

**Indexes:**

- `accounts(customer_id, account_id)`
- `account_devices(device_id, account_id)`
- `transfers(sender_id, occurred_at) INCLUDE (receiver_id, amount_rwf, transfer_id)`
- `transfers(receiver_id, occurred_at) INCLUDE (sender_id, amount_rwf, transfer_id)`
- BRIN on `transfers(occurred_at)`

**Checks** (`outputs/2_2_checks.txt`):

- All five row counts match capture.py (20,993,500 in total).
- Roles: person 240,000, merchant 6,000, agent 2,000.
- Transfer audit: 20,003,300 rows, earliest 1788235200, latest 1790798399, sum 231,482,327,870. This is **identical to capture.py**.
- All 13 constraints show `convalidated = t` (5 PK, 5 FK, 3 CHECK). Every table has all columns NOT NULL.

| Size (1 GB = 10⁹ bytes) | Data GB | Index GB | Total GB |
|---|---:|---:|---:|
| transfers | 1.206 | 2.434 | 3.639 |
| all five tables | 1.250 | 2.468 | 3.718 |
| database `momo` | | | 3.726 |

---

## 3 Build Neo4j

### 3.1 Map the same facts

```
 (:Customer {customer_id, region})
        │
        │ :OWNS                       (248,000; one per account)
        ▼
 (:Account {account_id, role}) ──:TRANSFER {transfer_id, occurred_at, amount_rwf}──► (:Account)
        │                              (20,003,300; one relationship per event, repeats kept)
        │ :USED_DEVICE {first_day, last_day, observations}   (285,600)
        ▼
 (:Device {device_id, access_type})
```

| Source field | Graph element |
|---|---|
| customers.customer_id, region | `Customer.customer_id` (int), `Customer.region` |
| accounts.account_id, role | `Account.account_id` (int), `Account.role` |
| accounts.customer_id | `(:Customer)-[:OWNS]->(:Account)` (the FK becomes a relationship; the column is `:IGNORE`d on the node) |
| devices.device_id, access_type | `Device.device_id` (int), `Device.access_type` |
| account_devices.account_id, device_id | `(:Account)-[:USED_DEVICE]->(:Device)` endpoints |
| account_devices.first_day, last_day, observations | `USED_DEVICE` properties (int) |
| transfers.sender_id, receiver_id | `(:Account)-[:TRANSFER]->(:Account)` start/end |
| transfers.transfer_id, occurred_at, amount_rwf | `TRANSFER` properties (long, long, int) |

### 3.2 Prepare and import CSVs

`prepare_import.py` writes temporary copies to `import/`. It replaces only the header line and streams the
remaining rows, leaving `data/*.csv` unchanged. It uses separate `Customer`, `Account` and `Device` ID groups
and derives `owns.csv` from `accounts.csv` in `customer_id, account_id` column order. Preparing all files
took 3.1 s.

| Import file | Typed header |
|---|---|
| customers.csv | `customer_id:ID(Customer),region:string` |
| accounts.csv | `account_id:ID(Account),:IGNORE,role:string` |
| devices.csv | `device_id:ID(Device),access_type:string` |
| owns.csv | `:START_ID(Customer),:END_ID(Account)` |
| used_device.csv | `:START_ID(Account),:END_ID(Device),first_day:int,last_day:int,observations:int` |
| transfers.csv | `transfer_id:long,:START_ID(Account),:END_ID(Account),occurred_at:long,amount_rwf:int` |

The import was run with the database stopped:

```
neo4j-admin database import full neo4j --overwrite-destination --id-type=integer \
  --nodes=Customer=import/customers.csv --nodes=Account=import/accounts.csv --nodes=Device=import/devices.csv \
  --relationships=OWNS=import/owns.csv --relationships=USED_DEVICE=import/used_device.csv \
  --relationships=TRANSFER=import/transfers.csv
```

| Step | Run 1 | Run 2 | Run 3 (screenshots 11–15) |
|---|---:|---:|---:|
| Import | 35.8 s (40 s wall) | 69.8 s (77 s wall) | **35.3 s (40.3 s wall)** |
| Constraints and index until `ONLINE` 100% | 34.0 s | 48 s | **33.2 s** |
| Store size | 2.051 GB | 2.049 GB | **2.064 GB** (`du`) |
| Transaction logs | 0.000016 GB | 0.000010 GB | **0.000016 GB** |

Every run imported 704,600 nodes, 20,536,900 relationships and 62,275,900 properties, with peak memory
1.04 GiB and an empty bad-row report. The constraints are three uniqueness constraints (Customer, Account and
Device IDs), plus a range index on `TRANSFER.occurred_at`. The offline import writes no transactions, which
is why the transaction logs are almost empty.

In run 3, the importer warned that only 135 MiB of memory was free. That is the likely cause of the slow
run 2: an 8 GB machine with PostgreSQL also running. Use run 3 as the reported figure, since it matches the
screenshots, and mention the variation.

**Checks** (`outputs/3_2_checks.txt`):

- Customer 228,000, Account 248,000, Device 228,600 (704,600 nodes).
- OWNS 248,000, USED_DEVICE 285,600, TRANSFER 20,003,300 (20,536,900 relationships).
- Roles: 240,000 / 6,000 / 2,000.
- All 248,000 accounts have exactly one owner.
- There are 20,003,300 distinct `transfer_id` values (1 to 20,003,300).
- Audit: 1788235200 / 1790798399 / 231,482,327,870. **Identical to capture.py and PostgreSQL.**

The temporary import copies were removed after the checks.

### 3.3 Inspect one account in both models

Account **998** (set A), traced through a JOIN in SQL and a MATCH in Cypher (`questions.py`), gives
identical rows in both engines:

| account | role | owner | region | device | access | days | obs | transfer | receiver | time (CAT) | RWF |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 998 | person | 998 | Kigali | 998 | handset | 0–29 | 39 | 113540 | 240004 | 2026-09-01 08:43:29 | 2,100 |

**How foreign keys become relationships.** Each FK column becomes a stored, directed relationship:

- `accounts.customer_id` becomes `OWNS`.
- The two FKs of the junction table `account_devices` become one `USED_DEVICE` relationship. Its non-key
  columns become relationship properties.
- `transfers.sender_id` and `receiver_id` become the start and end of a `TRANSFER` relationship, which
  carries the event columns.

SQL finds a match at query time by comparing key values (through the index). Neo4j stores the link, so it
follows a pointer from the node instead.

**What collapsing repeated payments would lose.** The month has 20,003,300 transfers but only 8,103,289
distinct sender→receiver pairs, so one edge per pair would erase 11,900,011 events. Account 998 alone repeats
payments to 16 receivers. For example, it paid account 1111 nine times between 2 and 29 Sep (117,700 RWF in total).

A single edge would lose:

- each `transfer_id`
- each timestamp, and with it the order and gaps between events
- each individual amount

Without those, Q1's hour window, Q2's daily totals, and the time-ordered chains and cycles in Q5/Q6 would
become impossible or wrong. At best, a sum or count would be left on the edge.

---

## 4 Answer routine business questions

The review hour is 09:45:00 inclusive to 10:45:00 exclusive CAT. The boundaries are converted to epoch
seconds in Python with `zoneinfo('Africa/Kigali')` (`questions.review_hour`).

### 4.1 Q1 Account activity

| Set | Account | Date | Start epoch | End epoch | PG count / RWF | Neo4j count / RWF | Match |
|---|---:|---|---:|---:|---|---|---|
| A | 998 | 6 Sep | 1788680700 | 1788684300 | 1 / 200,000 | 1 / 200,000 | yes |
| B | 147228 | 13 Sep | 1789285500 | 1789289100 | 1 / 1,050,000 | 1 / 1,050,000 | yes |
| C | 206978 | 8 Sep | 1788853500 | 1788857100 | 1 / 300,000 | 1 / 300,000 | yes |
| D | 237998 | 6 Sep | 1788680700 | 1788684300 | 1 / 45,000 | 1 / 45,000 | yes |
| E | 144228 | 13 Sep | 1789285500 | 1789289100 | 1 / 40,000 | 1 / 40,000 | yes |
| F | 203978 | 8 Sep | 1788853500 | 1788857100 | 1 / 30,000 | 1 / 30,000 | yes |

Each account made one outgoing transfer in its hour. A, B and C sent far more (200,000 to 1,050,000 RWF)
than their paired accounts D, E and F (30,000 to 45,000 RWF).

**Why outgoing value is not a balance.** A balance is opening balance + money in − money out − fees ±
reversals, measured at a point in time. Q1 counts only one direction (outflows) in a one-hour window. It
ignores incoming transfers, the opening balance, and cash deposited or withdrawn outside wallet-to-wallet
transfers. The dataset is explicitly not a complete ledger: it has no fees, reversals or cash balances.

### 4.2 Q2 Daily activity

SQL groups `(to_timestamp(occurred_at) AT TIME ZONE 'Africa/Kigali')::date`. Cypher groups
`date(datetime({epochSeconds: t.occurred_at, timezone: 'Africa/Kigali'}))`.

- Both engines return the same **30 days**, identical row by row.
- The daily sums reconcile exactly to the capture: **20,003,300 transfers and 231,482,327,870 RWF**.
- The full table is in `outputs/4_2_q2.txt` and the chart in `outputs/q2_daily_activity.png`.

**Pattern.** Most days carry an almost constant 666,666–666,667 transfers worth about 7.67 billion RWF.

- **6–15 Sep:** 150–331 extra transfers per day (2,496 in total), with daily value 50–190 million RWF above
  the baseline. So the extra transfers are few but large.
- **16–27 Sep:** a smaller excess of 30–121 transfers per day, with value back near the baseline. So these
  extra transfers are small.

These deviations are small: below 0.05% of the daily count and at most about 2.5% of the daily value.
That's why the chart's y-axes don't start at zero; the structure isn't visible in a zero-based chart, but it matches the review dates used later (6, 8 and 13 Sep).

**Why transfer value isn't provider revenue.** Revenue comes from fees and commissions, which aren't in
this data. Many transfer types (for example small P2P transfers or merchant payments) may carry low or zero
fees. Agent commissions are a cost to the provider. The same money is counted again each time it moves on.
So 231 billion RWF is gross payment flow, not income.

Single run, not a benchmark: PostgreSQL took 5.5 s and Neo4j 67.4 s for this full-month aggregation
(screenshot 18). Formal
timing is in section 6.2.

### 4.3 Q3 Shared devices

The SQL self-joins `account_devices` on `device_id`. The Cypher matches
`(Account)-[:USED_DEVICE]->(Device)<-[:USED_DEVICE]-(Account)`. Both keep pairs where
`max(first_day) <= min(last_day)` and exclude the review account.

| Set | Review account | Rows (PG / Neo4j) | Match |
|---|---:|---|---|
| A | 998 | 4 / 4 | yes |
| B | 147228 | 9 / 9 | yes |
| C | 206978 | 9 / 9 | yes |
| D | 237998 | 4 / 4 | yes |
| E | 144228 | 9 / 9 | yes |
| F | 203978 | 9 / 9 | yes |

Each review account's sharing falls into two groups:

1. **Its own phone.** Account 998 shares device 998 with account 220998, which belongs to the **same customer
   (998)**: a second wallet on the same handset. Similarly, 237998 shares with 17998, both owned by customer
   17998. In B, C, E and F, four other accounts with neighbouring IDs share one handset, all owned by different
   customers in the **same region**. This looks like a household phone. In C and F, one member's interval
   starts on day 11 (for example `[11, 29]`).
2. **A second handset (device IDs 228xxx).** This is shared with 3–5 accounts owned by **different customers,
   often in other provinces** (for example, C's device 228043 links Southern, Eastern, Northern and Western
   accounts). Each of these devices includes that set's **destination account** (24755, 186823, 6573, 21755,
   183823, 3573). This is a lead for sections 5 and 8, not a conclusion.

All shared devices for these six accounts are handsets. No public terminals appear.

**A legitimate sharing scenario.** Family members without their own phones use one household handset for
their separate wallets. Similarly, one person may keep a personal and a secondary wallet on the same phone.

**Why overlap does not prove simultaneous use.** Intervals are whole days and record only the first and
last day of observation. Intervals `[2,7]` and `[5,11]` overlap on days 5 to 7, but the two accounts might
have been observed on different days within that range, or hours apart on the same day. The phone could also
have been handed over, resold or reset in between. Observations show that a wallet was seen on a device, not
that it initiated a payment from it.
