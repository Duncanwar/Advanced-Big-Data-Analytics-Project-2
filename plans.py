"""6.2 / 6.3 Execution plans, collected outside timing."""
import sys

import db
from config import OUTPUT_DIR
from questions import (Q2_CYPHER, Q2_SQL, Q4_SQL, Q7_SQL, Q7_SQL_BIDIRECTIONAL, q4_cypher, q7_cypher, q7_params,
                       set_params)

PLAN_DIR = OUTPUT_DIR / 'plans'
B = set_params('B')
CASES = [
    ('Q2_month', Q2_SQL, Q2_CYPHER, {}),
    ('Q4_B_depth10', Q4_SQL, q4_cypher(10), dict(B, depth=10)),
    ('Q7_B_bound6', Q7_SQL, q7_cypher(6), q7_params(B, 6)),
]


def pg_plans():
    cases = CASES + [('Q7_B_bound6_bidirectional', Q7_SQL_BIDIRECTIONAL, None, q7_params(B, 6))]
    db.run_pg("SET statement_timeout = '600s'")
    for name, sql, _, params in cases:
        lines = [r[0] for r in db.run_pg('EXPLAIN (ANALYZE, BUFFERS) ' + sql, params)]
        (PLAN_DIR / f'pg_{name}.txt').write_text('\n'.join(lines) + '\n')
        print(f'--- PostgreSQL {name}: {lines[-1].strip()}')
        for line in lines:
            if any(k in line for k in ('Recursive Union', 'WorkTable Scan', 'Nested Loop', 'HashAggregate',
                                       'GroupAggregate', 'Seq Scan', 'Index Only Scan', 'Index Scan', 'Sort',
                                       'Gather', 'Hash Join', 'Merge Join', 'CTE Scan')) and 'actual' in line:
                print('   ' + line.strip()[:170])


def format_profile(plan, depth=0, out=None):
    out = [] if out is None else out
    args = plan.get('args', {})
    detail = str(args.get('Details', ''))[:90]
    out.append(f'{"  " * depth}{plan["operatorType"]:<40} rows {plan.get("rows", 0):>10,}  '
               f'dbHits {plan.get("dbHits", 0):>12,}  {detail}')
    for child in plan.get('children', []):
        format_profile(child, depth + 1, out)
    return out


def neo_plans():
    for name, _, cypher, params in CASES:
        with db.neo().session(database='neo4j') as session:
            summary = session.run('PROFILE ' + cypher, params).consume()
        lines = format_profile(summary.profile)
        total_hits = sum(int(l.split('dbHits')[1].split()[0].replace(',', '')) for l in lines)
        text = '\n'.join(lines)
        (PLAN_DIR / f'neo_{name}.txt').write_text(text + f'\n\ntotal dbHits {total_hits:,}\n')
        print(f'--- Neo4j {name}: total dbHits {total_hits:,}, '
              f'result available after {summary.result_available_after} ms, consumed after {summary.result_consumed_after} ms')
        print(text)


if __name__ == '__main__':
    PLAN_DIR.mkdir(exist_ok=True)
    {'pg': pg_plans, 'neo': neo_plans}[sys.argv[1]]()
    db.close()
