# Screenshots: Sections 1 to 4

All screenshots are in `screenshots/` and were taken on Sun 25 Oct 2026, 14:12–14:31 CAT. Each one shows
the executed command, its result, the macOS menu-bar clock and the Dock. Each was produced by a real run on
this machine with `tools/shot.sh`, which opens a Terminal window, runs the command and captures the screen.

| File | Report section | Shows |
|---|---|---|
| `01_1-1_workspace_info.png` | 1.1 | CPU, RAM, OS, Python/driver versions, generator hash, PostgreSQL connection and settings, Neo4j connection and memory settings |
| `02_1-1_postgres_settings.png` | 1.1 | psql connection (`\conninfo`), version, `TimeZone = Africa/Kigali`, shared_buffers, work_mem |
| `03_1-1_neo4j_status.png` | 1.1 | Neo4j 5.26.0 running, Community edition, `neo4j` default database online |
| `04a_1-2_preview_part1.png` | 1.2 | `dataset_info()`, `FIELDS`, first 10 customers |
| `04b_1-2_preview_part2.png` | 1.2 | First 10 accounts, devices, account_devices, transfers |
| `05_1-2_capture_totals.png` | 1.2 | Million-row log, five-stream totals (all `yes`), seconds, CSV MB, transfer audit |
| `08_2-1_definitions_part1.png` | 2.1 | `\d` customers, accounts, devices: types, NOT NULL, PKs, FKs |
| `09_2-1_definitions_part2.png` | 2.1 | `\d` account_devices, transfers: CHECK constraints, FKs, indexes |
| `06_2-2_load.png` | 2.2 | `\copy` of all five files with load times |
| `07_2-2_constraints_indexes.png` | 2.2 | PK/FK/index/ANALYZE setup times |
| `10a_2-2_checks_counts_audit_constraints.png` | 2.2 | Row counts, roles, audit totals, 13 validated constraints, NOT NULL |
| `10b_2-2_checks_indexes_sizes.png` | 2.2 | Index definitions, data/index GB, database 3.726 GB |
| `11_3-2_prepare_import.png` | 3.2 | `prepare_import.py` typed headers and owns.csv, Neo4j stopped |
| `12_3-2_import.png` | 3.2 | Full import command, `IMPORT DONE in 35s`, 704600 nodes, 20536900 relationships |
| `13_3-2_constraints_indexes.png` | 3.2 | 3 uniqueness constraints, TRANSFER.occurred_at range index, all ONLINE 100%, 33.2 s |
| `14_3-2_checks_sizes.png` | 3.2 | Node/relationship counts, roles, one owner each, unique transfer_id, audit totals, store/tx-log GB |
| `15_3-2_remove_import_copies.png` | 3.2 | Temporary import copies listed, then removed; source CSVs kept |
| `16a_3-3_trace_account_998.png` | 3.3 | Identical SQL JOIN and Cypher MATCH records for account 998 |
| `16b_3-3_repeated_payments.png` | 3.3 | Repeated payments that one collapsed edge would hide; 11,900,011 events in total |
| `20a_queries_3-3.png` | 3.3 | Trace and repeated-payment query pairs |
| `17_4-1_q1.png` | 4.1 | Six paired Q1 results, all `yes` |
| `20b_queries_q1_q2.png` | 4.1, 4.2 | Q1 and Q2 SQL/Cypher pairs |
| `18_4-2_q2.png` | 4.2 | 30-day table, PG = Neo4j, count and sum reconciliation |
| `21_4-2_q2_chart.png` | 4.2 | Q2 daily count and value chart |
| `19a_4-3_q3_sets_A-D.png` | 4.3 | Q3 rows for sets A to D |
| `19b_4-3_q3_sets_E-F_summary.png` | 4.3 | Q3 rows for sets E and F, plus the six-set count summary |
| `20c_queries_q3.png` | 4.3 | Q3 SQL/Cypher pair |

To retake any one of them, run, for example:

```bash
tools/shot.sh 17_4-1_q1 'python run_part1.py q1'
```
