"""6.2 / 6.3 Timing: 21 fixed cases per engine, 3 untimed warm-ups then 5 measured runs each."""
import argparse
import csv
import json
import statistics
import time
from datetime import datetime

import psycopg
from neo4j import Query
from neo4j.exceptions import ClientError

import db
from cases import timed_cases
from config import OUTPUT_DIR
from db import normalize
from questions import KIGALI

WARMUPS, RUNS = 3, 5
WARMUP_TIMEOUT, RUN_TIMEOUT = 180, 60
FIELDS = ('case', 'params', 'engine', 'phase', 'run', 'start_cat', 'duration_ms', 'rows', 'status', 'correct')


def runner(engine):
    if engine == 'pg':
        conn = db.pg()

        def run(case, timeout):
            with conn.cursor() as cur:
                cur.execute(f"SET statement_timeout = '{timeout}s'")
                cur.execute(case.sql, case.params)
                return cur.fetchall()
        return run

    driver = db.neo()

    def run(case, timeout):
        with driver.session(database='neo4j') as session:
            return [tuple(r.values()) for r in session.run(Query(case.cypher, timeout=timeout), case.params)]
    return run


def expected_answers():
    answers = {}
    for path in sorted(OUTPUT_DIR.glob('6_1_results_*.json')):
        for r in json.loads(path.read_text()):
            answers[r['case']] = json.dumps(r['answer'], default=str)
    return answers


def bench(engine, cases, tag):
    run = runner(engine)
    expected = expected_answers()
    out = OUTPUT_DIR / f'6_2_runs_{engine}_{tag}.csv'
    with open(out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for case in cases:
            for phase, count, timeout in (('warmup', WARMUPS, WARMUP_TIMEOUT), ('measured', RUNS, RUN_TIMEOUT)):
                for i in range(1, count + 1):
                    start_cat = datetime.now(KIGALI).strftime('%Y-%m-%d %H:%M:%S')
                    rows, status = None, 'ok'
                    start = time.perf_counter()
                    try:
                        rows = run(case, timeout)
                    except (psycopg.errors.QueryCanceled, TimeoutError) as e:
                        status = 'timeout'
                    except ClientError as e:
                        status = 'timeout' if 'Timeout' in (e.code or '') or 'timeout' in str(e).lower() else 'error'
                    except Exception:
                        status = 'error'
                    duration = time.perf_counter() - start
                    correct = ''
                    if rows is not None:
                        correct = str(json.dumps(normalize(rows), default=str) == expected.get(case.case_id))
                    writer.writerow(dict(case=case.case_id, params=json.dumps(case.params), engine=engine, phase=phase,
                                         run=i, start_cat=start_cat,
                                         duration_ms=f'{duration * 1000:.1f}' if status == 'ok' else '',
                                         rows=len(rows) if rows is not None else '', status=status, correct=correct))
                    f.flush()
                    if phase == 'measured':
                        shown = f'{duration * 1000:9.1f} ms' if status == 'ok' else f'{status.upper():>12}'
                        print(f'{engine:<4}{case.case_id:<11} run {i}  {start_cat}  {shown}  rows {rows and len(rows)}'
                              f'  correct {correct}', flush=True)
    print(f'saved {out.relative_to(OUTPUT_DIR.parent)}')


def summary():
    stats = {}
    for path in sorted(OUTPUT_DIR.glob('6_2_runs_*.csv')):
        tag = path.stem.split('_', 4)[-1]
        with open(path) as f:
            for r in csv.DictReader(f):
                if r['phase'] != 'measured':
                    continue
                key = (r['case'], tag)
                entry = stats.setdefault(key, {}).setdefault(r['engine'], dict(ms=[], timeouts=0, errors=0, wrong=0))
                if r['status'] == 'ok':
                    entry['ms'].append(float(r['duration_ms']))
                    entry['wrong'] += r['correct'] != 'True'
                else:
                    entry['timeouts' if r['status'] == 'timeout' else 'errors'] += 1

    def describe(e):
        if not e:
            return f'{"-":>28}'
        if not e['ms']:
            return f'{"all " + str(e["timeouts"]) + " timed out":>28}'
        note = f' ({e["timeouts"]}T)' if e['timeouts'] else ''
        return f'{statistics.median(e["ms"]):>9.1f}{min(e["ms"]):>9.1f}{max(e["ms"]):>10.1f}{note}'

    print(f'{"case":<11}{"version":<10}{"PG median":>9}{"min":>9}{"max":>10}   {"Neo median":>9}{"min":>9}{"max":>10}'
          f'{"PG/Neo":>9}  wrong')
    for (case, tag), engines in stats.items():
        pg, neo = engines.get('pg'), engines.get('neo') or stats.get((case, 'original'), {}).get('neo')
        ratio = (f'{statistics.median(pg["ms"]) / statistics.median(neo["ms"]):9.2f}'
                 if pg and neo and pg['ms'] and neo['ms'] else f'{"-":>9}')
        wrong = sum(e['wrong'] for e in engines.values())
        print(f'{case:<11}{tag:<10}{describe(pg)}   {describe(neo)}{ratio}  {wrong}')
    print('ms = milliseconds over 5 measured runs after 3 warm-ups; T = timed-out runs (> 60 s), excluded from statistics')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('pg', 'neo'))
    parser.add_argument('--q7', default='naive', choices=('naive', 'bidir'))
    parser.add_argument('--only')
    parser.add_argument('--tag', default='original')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if args.summary:
        summary()
        return
    cases = [c for c in timed_cases(args.q7) if not args.only or c.question == args.only]
    print(f'=== 6.2 timing: engine {args.engine}, {len(cases)} cases, {WARMUPS} warm-ups + {RUNS} measured runs each')
    bench(args.engine, cases, args.tag)
    db.close()


if __name__ == '__main__':
    main()
