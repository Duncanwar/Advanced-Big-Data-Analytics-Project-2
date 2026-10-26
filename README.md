# Advanced-Big-Data-Analytics-Project-2

Mobile money investigations with PostgreSQL and Neo4j (September 2026 records).

## Environment

| Component | Version / setting |
|---|---|
| Machine | Apple M2, 8 cores, 8 GB RAM, macOS 14.6.1 |
| PostgreSQL | 16.8 (Postgres.app), database `momo`, time zone `Africa/Kigali` |
| Neo4j | 5.26.0 Community (tarball in `~/neo4j-mm/neo4j-community-5.26.0`), Java 17, default `neo4j` database, heap 2 GB, page cache 2 GB |
| Python | 3.13 in `.venv`: numpy, psycopg 3, neo4j driver, matplotlib |

`mobile_money_generator.py` is the supplied file, unchanged
(sha256 `2ea0e59d2b7b987d84a3d151bd9d1ad7b3052bfbc25abf1466c8e94467e9455a`).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install numpy "psycopg[binary]" neo4j matplotlib
cp .env.example .env          # then put your Neo4j password in .env
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export NEO4J_HOME=~/neo4j-mm/neo4j-community-5.26.0
createdb momo
psql -d momo -c "ALTER DATABASE momo SET timezone TO 'Africa/Kigali';"
```

## Run in this order

```bash
# 1.1 workspace, versions, settings and both connections
.venv/bin/python workspace_info.py | tee outputs/1_1_workspace.txt

# 1.2 capture the five streams to data/*.csv (about 75 s)
.venv/bin/python capture.py | tee outputs/1_2_capture.txt

# 2.1-2.2 PostgreSQL: tables, bulk load, keys/indexes, checks
psql -d momo -f sql/01_tables.sql
psql -d momo -f sql/02_load.sql                | tee outputs/2_2_load.txt
psql -d momo -f sql/03_constraints_indexes.sql | tee outputs/2_2_constraints_indexes.txt
psql -d momo -f sql/04_checks.sql              | tee outputs/2_2_checks.txt

# 3.2 Neo4j: typed import copies (prepare_import.py), full import with the database stopped,
#     constraints/index (cypher/01_*), checks (cypher/02_*), sizes, then remove the import copies
./neo4j_import.sh

# 3.3 and Q1-Q3 on both engines (Q2 also writes outputs/q2_daily_activity.png)
.venv/bin/python run_part1.py trace q1 q3 | tee outputs/3_3_q1_q3.txt
.venv/bin/python run_part1.py q2          | tee outputs/4_2_q2.txt
```

```bash
# 5 Q4-Q7 on both engines (Q4 also writes outputs/q4_count_vs_depth.png)
.venv/bin/python run_part2.py | tee outputs/5_results.txt

# 6.1 correctness: 61 cases, Q7 paths, independent CSV checks
.venv/bin/python compare.py | tee outputs/6_1_compare.txt

# 6.2 timing, one service at a time, then the summary and plans
tools/services.sh neo stop; .venv/bin/python bench.py --engine pg
tools/services.sh pg stop;  tools/services.sh neo start; .venv/bin/python bench.py --engine neo
tools/services.sh pg start; .venv/bin/python bench.py --summary
.venv/bin/python plans.py pg; .venv/bin/python plans.py neo

# 6.3 improved Q7 SQL: recheck 12 cases, retime B/E at both bounds
.venv/bin/python compare.py --only Q7 --q7 bidir
tools/services.sh neo stop; .venv/bin/python bench.py --engine pg --q7 bidir --only Q7 --tag improved
tools/services.sh neo start; .venv/bin/python bench.py --summary

# 7 load test (each engine with the other stopped), then summary and plots
tools/services.sh neo stop; .venv/bin/python loadtest.py --engine pg --all
tools/services.sh pg stop;  tools/services.sh neo start; .venv/bin/python loadtest.py --engine neo --all
tools/services.sh pg start; .venv/bin/python loadtest.py --summary

# report (Word + PDF) from report/report.md
report/build_report.sh
```

## Layout

| Path | Purpose |
|---|---|
| `capture.py` | 1.2 stream the generator into CSVs with counts and audit totals |
| `config.py`, `.env.example` | connection settings (real secrets stay in the uncommitted `.env`) |
| `sql/` | PostgreSQL definitions, load, constraints/indexes and checks |
| `prepare_import.py`, `cypher/` | Neo4j typed import copies, constraints/indexes and checks |
| `db.py` | persistent connections with `run_pg` / `run_neo` |
| `questions.py` | parameterized SQL/Cypher pairs |
| `run_part1.py` | 3.3 and Q1 to Q3 on both engines with answer comparison |
| `run_part2.py` | Section 5, Q4 to Q7 with evidence and the Q4 plot |
| `cases.py`, `compare.py` | 6.1 the 61 cases and the correctness comparison |
| `bench.py`, `plans.py` | 6.2/6.3 timing runs, summary, EXPLAIN ANALYZE and PROFILE |
| `loadtest.py` | Section 7 multiprocessing load test, summary and plots |
| `tools/` | `services.sh` (start/stop each database), `shot.sh` (screenshots) |
| `report/` | report source, images and the built Word/PDF report |
| `outputs/` | full outputs, raw timing runs, plans and charts |
| `docs/` | report notes |

CSV files (`data/`, `import/`) and database stores stay local and are not committed.
