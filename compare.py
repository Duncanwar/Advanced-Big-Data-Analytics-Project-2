"""6.1 Correctness: run all 61 cases on both engines, normalize, sort and compare exactly."""
import argparse
import csv
import json
import time

from cases import all_cases
from config import DATA_DIR, OUTPUT_DIR
from db import close, normalize, run_neo, run_pg
from questions import (Q7_PATH_CHECK_SQL, Q3_SQL, Q5_SQL, Q6_SQL, SETS, q7_params, q7_path_cypher,
                       set_params)


def run_cases(cases):
    results = []
    for case in cases:
        t = time.perf_counter()
        pg_rows = normalize(run_pg(case.sql, case.params))
        pg_s = time.perf_counter() - t
        t = time.perf_counter()
        neo_rows = normalize(run_neo(case.cypher, case.params))
        neo_s = time.perf_counter() - t
        results.append(dict(case=case.case_id, question=case.question, label=case.label,
                            pg_rows=len(pg_rows), neo_rows=len(neo_rows), match=pg_rows == neo_rows,
                            pg_s=pg_s, neo_s=neo_s, answer=pg_rows))
    return results


def print_table(results):
    cell = '{:<11}{:>5}{:>6}{:>8}{:>8}  {:<5}'
    head = cell.format('case', 'PG', 'Neo', 'PG s', 'Neo s', 'ok')
    print(f'{head}   |   {head}')
    half = (len(results) + 1) // 2
    for left, right in zip(results[:half], results[half:] + [None]):
        row = [cell.format(r['case'], r['pg_rows'], r['neo_rows'], f'{r["pg_s"]:.2f}', f'{r["neo_s"]:.2f}',
                           'yes' if r['match'] else 'NO')
               for r in (left, right) if r]
        print('   |   '.join(row))
    by_question = {}
    for r in results:
        total, ok = by_question.get(r['question'], (0, 0))
        by_question[r['question']] = (total + 1, ok + r['match'])
    print('\n' + '  '.join(f'{q}: {ok}/{total}' for q, (total, ok) in by_question.items()))
    matched = sum(r['match'] for r in results)
    print(f'TOTAL {matched}/{len(results)} cases identical (rows normalized to plain integers/dates and sorted)')


def check_q7_paths(results):
    print('\n-- Q7 supporting paths (lengths compared above; paths validated separately)')
    for r in results:
        if r['question'] != 'Q7' or r['answer'][0][0] is None:
            continue
        name, bound = r['case'].split('-')[1], int(r['case'].split('-b')[1])
        params = q7_params(set_params(name), bound)
        accounts, transfers = run_neo(q7_path_cypher(bound), params)[0]
        checks = run_pg(Q7_PATH_CHECK_SQL, dict(accounts=accounts, transfers=transfers))
        ok = (len(transfers) == r['answer'][0][0]
              and all(c[1] is not None and c[4] == 'person' and c[5] == 'person' and c[6] for c in checks))
        print(f'{r["case"]:<10} length {len(transfers)}  accounts {accounts}  valid: {"yes" if ok else "NO"}')


def check_csv():
    """Independent checks against the captured CSV rows, without either database."""
    print('\n-- independent CSV checks (data/*.csv, plain Python)')
    account, other, device = SETS['C'][0], 206976, 206976
    rows = {}
    with open(DATA_DIR / 'account_devices.csv', newline='') as f:
        for row in csv.DictReader(f):
            if row['device_id'] == str(device) and row['account_id'] in (str(account), str(other)):
                rows[int(row['account_id'])] = (int(row['first_day']), int(row['last_day']))
    start, end = max(rows[account][0], rows[other][0]), min(rows[account][1], rows[other][1])
    db_rows = run_pg(Q3_SQL, dict(account=account))
    print(f'device overlap: account {account} {rows[account]} and {other} {rows[other]} on device {device}'
          f' -> overlap [{start}, {end}]; Q3 row {[r for r in db_rows if r[0] == other and r[1] == device]}'
          f' agrees: {"yes" if (other, device, "handset", start, end) in db_rows else "NO"}')

    params = set_params('A')
    cycle = list(normalize(run_pg(Q6_SQL, params))[0][0])
    chain = list(normalize(run_pg(Q5_SQL, params))[0][:3])
    wanted = set(cycle) | set(chain)
    found = {}
    with open(DATA_DIR / 'transfers.csv', newline='') as f:
        for row in csv.DictReader(f):
            if int(row['transfer_id']) in wanted:
                found[int(row['transfer_id'])] = {k: int(v) for k, v in row.items()}
    for label, ids in (('Q5 chain', chain), ('Q6 cycle', cycle)):
        t = [found[i] for i in ids]
        linked = all(a['receiver_id'] == b['sender_id'] for a, b in zip(t, t[1:]))
        ordered = all(a['occurred_at'] < b['occurred_at'] for a, b in zip(t, t[1:]))
        amounts = all(90 * a['amount_rwf'] <= 100 * b['amount_rwf'] <= 105 * a['amount_rwf'] for a, b in zip(t, t[1:]))
        starts = t[0]['sender_id'] == params['account'] and params['start'] <= t[0]['occurred_at'] < params['end']
        if label == 'Q5 chain':
            timing = all(b['occurred_at'] - a['occurred_at'] <= 600 for a, b in zip(t, t[1:]))
            accounts = [t[0]['sender_id']] + [x['receiver_id'] for x in t]
            shape = len(set(accounts)) == 4
        else:
            timing = t[-1]['occurred_at'] - t[0]['occurred_at'] <= 1800 and t[-1]['occurred_at'] < params['end']
            shape = t[-1]['receiver_id'] == params['account']
        ok = all((linked, ordered, amounts, starts, timing, shape))
        print(f'{label} {ids}: linked {linked}, increasing {ordered}, amounts 90-105% {amounts}, '
              f'starts in hour {starts}, timing {timing}, shape {shape} -> {"valid" if ok else "INVALID"}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--q7', default='naive', choices=('naive', 'bidir'))
    parser.add_argument('--only', help='question prefix, e.g. Q7')
    args = parser.parse_args()
    cases = [c for c in all_cases(args.q7) if not args.only or c.question == args.only]
    print(f'=== 6.1 Correctness: {len(cases)} cases, Q7 SQL version: {args.q7}')
    results = run_cases(cases)
    print_table(results)
    check_q7_paths(results)
    tag = f'{args.only or "all"}_{args.q7}'
    (OUTPUT_DIR / f'6_1_results_{tag}.json').write_text(json.dumps(results, default=str, indent=1))
    if not args.only:
        check_csv()
    close()


if __name__ == '__main__':
    main()
