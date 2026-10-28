"""Capture the five mobile-money streams to CSV files, with row counts and audit totals."""
import csv
import os
import time
from datetime import datetime, timedelta, timezone
from itertools import islice
from pprint import pprint

import mobile_money_generator as g

STREAMS = {
    'customers': g.iter_customers,
    'accounts': g.iter_accounts,
    'devices': g.iter_devices,
    'account_devices': g.iter_account_devices,
    'transfers': g.iter_transfers,
}
EXPECTED = g.dataset_info()['expected_counts']
OUT_DIR = 'data'
LOG_EVERY = 1_000_000
CAT = timezone(timedelta(hours=2))


def preview(n=10):
    print('=== dataset_info() ===')
    pprint(g.dataset_info(), sort_dicts=False)
    print('\n=== FIELDS ===')
    pprint(g.FIELDS, sort_dicts=False)
    for name, stream in STREAMS.items():
        print(f'\n=== {name}: first {n} records ===')
        for row in islice(stream(), n):
            print(row)


def capture(name, stream):
    path = os.path.join(OUT_DIR, f'{name}.csv')
    consumed = written = 0
    audit = dict(count=0, earliest=None, latest=None, amount_rwf=0)
    start = time.perf_counter()
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=g.FIELDS[name])
        writer.writeheader()
        for row in stream():
            consumed += 1
            writer.writerow(row)
            written += 1
            if name == 'transfers':
                t = row['occurred_at']
                audit['count'] += 1
                audit['amount_rwf'] += row['amount_rwf']
                if audit['earliest'] is None or t < audit['earliest']:
                    audit['earliest'] = t
                if audit['latest'] is None or t > audit['latest']:
                    audit['latest'] = t
                if consumed % LOG_EVERY == 0:
                    print(f'  transfers: {consumed:>12,} rows  '
                          f'{time.perf_counter() - start:7.1f}s')
    seconds = time.perf_counter() - start
    return dict(stream=name, consumed=consumed, written=written, expected=EXPECTED[name],
                seconds=seconds, bytes=os.path.getsize(path), audit=audit)


def report(results, total_seconds):
    print(f'\n{"stream":<16}{"consumed":>13}{"written":>13}{"expected":>13}'
          f'{"match":>7}{"seconds":>10}{"CSV MB":>10}')
    for r in results:
        match = r['consumed'] == r['written'] == r['expected']
        print(f'{r["stream"]:<16}{r["consumed"]:>13,}{r["written"]:>13,}{r["expected"]:>13,}'
              f'{"yes" if match else "NO":>7}{r["seconds"]:>10.1f}{r["bytes"] / 1e6:>10.1f}')
    consumed = sum(r['consumed'] for r in results)
    written = sum(r['written'] for r in results)
    expected = sum(r['expected'] for r in results)
    size = sum(r['bytes'] for r in results)
    print(f'{"TOTAL":<16}{consumed:>13,}{written:>13,}{expected:>13,}'
          f'{"yes" if consumed == written == expected else "NO":>7}'
          f'{total_seconds:>10.1f}{size / 1e6:>10.1f}')

    audit = next(r['audit'] for r in results if r['stream'] == 'transfers')
    print('\n=== transfer audit ===')
    print(f'{"transfer count":<23}{audit["count"]:,}')
    for key in ('earliest', 'latest'):
        stamp = datetime.fromtimestamp(audit[key], CAT).strftime('%Y-%m-%d %H:%M:%S')
        print(f'{key + " occurred_at":<23}{audit[key]}  ({stamp} CAT)')
    print(f'{"sum amount_rwf":<23}{audit["amount_rwf"]:,} RWF')


def main():
    preview()
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f'\n=== capturing to {OUT_DIR}/ ===')
    start = time.perf_counter()
    results = []
    for name, stream in STREAMS.items():
        print(f'capturing {name} ...')
        results.append(capture(name, stream))
    report(results, time.perf_counter() - start)


if __name__ == '__main__':
    main()
