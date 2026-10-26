"""7.1 Concurrent requests: Q4 depth 10 and Q7 length-only bound 6, cycling sets A-B-C.

Each client is a process with one persistent connection. Clients warm up A-B-C once, then wait on a
Barrier; its release sets a common start time and a deadline 15 s later. Clients start cycles until
the deadline, finish any started cycle, and send each request immediately after the previous one.
Correctness is checked after timing against the 6.1 answers.

  python loadtest.py --engine pg --all        # both workloads x 1/4/8/16 clients x 3 repetitions
  python loadtest.py --engine neo --all
  python loadtest.py --engine pg --workload q7 --clients 16 --rep 1    # a single run
  python loadtest.py --summary                # medians of repetitions + plots
"""
import argparse
import csv
import json
import math
import multiprocessing as mp
import statistics
import threading
import time
from functools import partial

import psutil

from config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, OUTPUT_DIR, PG_DSN
from questions import (Q4_SQL, Q7_SQL_BIDIRECTIONAL, q4_cypher, q7_cypher, q7_params, set_params)

DURATION, TIMEOUT = 15, 60
CLIENTS = (1, 4, 8, 16)
REPS = 3
SETS_CYCLE = ('A', 'B', 'C')
RUN_FIELDS = ('engine', 'workload', 'clients', 'rep', 'elapsed_s', 'requests', 'correct', 'wrong', 'errors',
              'timeouts', 'throughput_rps', 'median_ms', 'p95_ms', 'cpu_mean', 'cpu_max')


def request_for(workload, name):
    params = set_params(name)
    if workload == 'q4':
        params = dict(params, depth=10)
        return Q4_SQL, q4_cypher(10), params, f'Q4-{name}-d10'
    return Q7_SQL_BIDIRECTIONAL, q7_cypher(6), q7_params(params, 6), f'Q7-{name}-b6'


def release(start_at, deadline_at):
    """Barrier action: runs once as the barrier releases, fixing the common start and deadline."""
    start_at.value = time.time()
    deadline_at.value = start_at.value + DURATION


def client(cid, engine, workload, barrier, start_at, deadline_at, results):
    from db import normalize
    if engine == 'pg':
        import psycopg
        conn = psycopg.connect(PG_DSN, autocommit=True, application_name='loadtest')
        conn.execute(f"SET statement_timeout = '{TIMEOUT}s'")

        def run(sql, cypher, params):
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
    else:
        from neo4j import GraphDatabase, Query
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        def run(sql, cypher, params):
            with driver.session(database='neo4j') as session:
                return [tuple(r.values()) for r in session.run(Query(cypher, timeout=TIMEOUT), params)]

    requests = [request_for(workload, name) for name in SETS_CYCLE]
    for sql, cypher, params, _ in requests:          # warm-up cycle A-B-C
        run(sql, cypher, params)
    barrier.wait()
    deadline = deadline_at.value
    log = []
    cycle = 0
    while time.time() < deadline:
        cycle += 1
        for sql, cypher, params, case_id in requests:
            sent = time.time()
            t = time.perf_counter()
            status, answer = 'ok', None
            try:
                answer = json.dumps(normalize(run(sql, cypher, params)), default=str)
            except Exception as e:
                status = 'timeout' if 'timeout' in str(e).lower() or 'cancel' in str(e).lower() else 'error'
            log.append(dict(client=cid, cycle=cycle, case=case_id, sent=sent, latency=time.perf_counter() - t,
                            status=status, answer=answer))
    results.put((cid, time.time(), log))
    if engine == 'pg':
        conn.close()
    else:
        driver.close()


def one_run(engine, workload, clients, rep, expected):
    barrier_start = mp.Value('d', 0.0)
    deadline_at = mp.Value('d', 0.0)
    barrier = mp.Barrier(clients, action=partial(release, barrier_start, deadline_at))
    results = mp.Queue()
    procs = [mp.Process(target=client, args=(i, engine, workload, barrier, barrier_start, deadline_at, results))
             for i in range(clients)]
    for p in procs:
        p.start()

    cpu, stop = [], threading.Event()

    def sample():
        psutil.cpu_percent(None)
        while not stop.is_set():
            time.sleep(0.5)
            cpu.append(psutil.cpu_percent(None))
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()

    collected = [results.get() for _ in procs]
    for p in procs:
        p.join()
    stop.set()
    sampler.join()

    start = barrier_start.value
    end = max(finish for _, finish, _ in collected)
    log = [entry for _, _, entries in collected for entry in entries]
    for entry in log:
        entry['correct'] = entry['status'] == 'ok' and entry['answer'] == expected[entry['case']]
    ok = sorted(e['latency'] for e in log if e['status'] == 'ok')
    correct = sum(e['correct'] for e in log)
    elapsed = end - start
    row = dict(engine=engine, workload=workload, clients=clients, rep=rep, elapsed_s=f'{elapsed:.2f}',
               requests=len(log), correct=correct, wrong=sum(e['status'] == 'ok' and not e['correct'] for e in log),
               errors=sum(e['status'] == 'error' for e in log), timeouts=sum(e['status'] == 'timeout' for e in log),
               throughput_rps=f'{correct / elapsed:.2f}',
               median_ms=f'{statistics.median(ok) * 1000:.1f}' if ok else '',
               p95_ms=f'{ok[math.ceil(0.95 * len(ok)) - 1] * 1000:.1f}' if ok else '',
               cpu_mean=f'{statistics.mean(cpu):.0f}' if cpu else '', cpu_max=f'{max(cpu):.0f}' if cpu else '')
    with open(OUTPUT_DIR / '7_requests.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        for e in log:
            writer.writerow((engine, workload, clients, rep, e['client'], e['cycle'], e['case'], f'{e["sent"]:.3f}',
                             f'{e["latency"] * 1000:.1f}', e['status'], e['correct']))
    path = OUTPUT_DIR / '7_runs.csv'
    new = not path.exists()
    with open(path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=RUN_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)
    print(f'{engine:<4}{workload:<4} clients {clients:>2} rep {rep}: {row["requests"]:>5} requests, '
          f'{correct:>5} correct, {row["errors"]} errors, {row["timeouts"]} timeouts, elapsed {elapsed:5.1f}s, '
          f'{row["throughput_rps"]:>7} req/s, median {row["median_ms"]:>7} ms, p95 {row["p95_ms"]:>7} ms, '
          f'CPU mean {row["cpu_mean"]}% max {row["cpu_max"]}%', flush=True)


def expected_answers():
    answers = {}
    for path in sorted(OUTPUT_DIR.glob('6_1_results_*.json')):
        for r in json.loads(path.read_text()):
            answers[r['case']] = json.dumps(r['answer'], default=str)
    return answers


def summary():
    with open(OUTPUT_DIR / '7_runs.csv') as f:
        runs = [r for r in csv.DictReader(f) if r['rep'] != '0']   # rep 0 = demonstration runs
    groups = {}
    for r in runs:
        groups.setdefault((r['engine'], r['workload'], int(r['clients'])), []).append(r)
    med = lambda rows, k: statistics.median(float(r[k]) for r in rows if r[k])
    print(f'{"engine":<7}{"workload":<9}{"clients":>8}{"reps":>5}{"throughput req/s":>17}{"median ms":>11}'
          f'{"p95 ms":>9}{"errors":>7}{"timeouts":>9}{"wrong":>6}{"CPU mean%":>10}')
    table = []
    for (engine, workload, clients), rows in sorted(groups.items()):
        t, m, p = med(rows, 'throughput_rps'), med(rows, 'median_ms'), med(rows, 'p95_ms')
        table.append((engine, workload, clients, t, p))
        print(f'{engine:<7}{workload:<9}{clients:>8}{len(rows):>5}{t:>17.2f}{m:>11.1f}{p:>9.1f}'
              f'{sum(int(r["errors"]) for r in rows):>7}{sum(int(r["timeouts"]) for r in rows):>9}'
              f'{sum(int(r["wrong"]) for r in rows):>6}{med(rows, "cpu_mean"):>10.0f}')
    print('each row = median of its repetitions; p95 = sorted successful latency at position ceil(0.95 n)')
    plot(table)


def plot(table):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = dict(pg='#2a78d6', neo='#eb6834')
    names = dict(pg='PostgreSQL', neo='Neo4j')
    titles = dict(q4='Q4 depth 10', q7='Q7 length-only bound 6')
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    for col, workload in enumerate(('q4', 'q7')):
        for row, (index, label) in enumerate(((3, 'Throughput (correct requests/s)'), (4, 'p95 latency (ms)'))):
            ax = axes[row][col]
            for engine in ('pg', 'neo'):
                pts = sorted((c, v[index]) for v in table for c in [v[2]] if v[0] == engine and v[1] == workload)
                if pts:
                    ax.plot([c for c, _ in pts], [y for _, y in pts], color=colors[engine], linewidth=2, marker='o',
                            markersize=6, label=names[engine])
                    ax.annotate(f'{pts[-1][1]:,.0f}', pts[-1], textcoords='offset points', xytext=(6, 0),
                                fontsize=8, color='#52514e', va='center')
            ax.set_title(f'{titles[workload]}: {label}', loc='left', fontsize=10)
            ax.set_xticks(CLIENTS)
            ax.set_ylim(bottom=0)
            ax.grid(axis='y', color='#e6e5e0')
            ax.set_axisbelow(True)
            for side in ('top', 'right'):
                ax.spines[side].set_visible(False)
            if row == 1:
                ax.set_xlabel('Concurrent clients', color='#52514e')
    axes[0][0].legend(frameon=False, fontsize=9)
    fig.suptitle('7.2 Throughput and p95 latency vs clients (median of 3 repetitions)', x=0.02, ha='left', fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / 'loadtest_scaling.png'
    fig.savefig(path, dpi=150)
    print(f'chart saved: {path.relative_to(OUTPUT_DIR.parent)}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', choices=('pg', 'neo'))
    parser.add_argument('--workload', choices=('q4', 'q7'))
    parser.add_argument('--clients', type=int)
    parser.add_argument('--rep', type=int, default=1)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if args.summary:
        summary()
        return
    expected = expected_answers()
    plan = ([(w, c, r) for w in ('q4', 'q7') for c in CLIENTS for r in range(1, REPS + 1)] if args.all
            else [(args.workload, args.clients, args.rep)])
    print(f'=== 7.1 load test: engine {args.engine}, {len(plan)} runs of {DURATION}s, timeout {TIMEOUT}s')
    for workload, clients, rep in plan:
        one_run(args.engine, workload, clients, rep, expected)


if __name__ == '__main__':
    main()
