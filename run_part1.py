"""Run 3.3 (inspect one account) and Q1 to Q3 on both engines and compare the answers."""
import sys
import time
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates
import matplotlib.pyplot as plt
import matplotlib.ticker

from config import OUTPUT_DIR
from db import close, normalize, run_neo, run_pg
from questions import (KIGALI, PAIRS_SQL, Q1_CYPHER, Q1_SQL, Q2_CYPHER, Q2_SQL, Q3_CYPHER, Q3_SQL,
                       REPEATS_CYPHER, REPEATS_SQL, SETS, TRACE_CYPHER, TRACE_SQL, set_params)

CAPTURE_COUNT = 20_003_300
CAPTURE_SUM_RWF = 231_482_327_870


def cat(epoch):
    return datetime.fromtimestamp(epoch, KIGALI).strftime('%Y-%m-%d %H:%M:%S')


def both(sql, cypher, params=None):
    t = time.perf_counter()
    pg_rows = run_pg(sql, params)
    pg_s = time.perf_counter() - t
    t = time.perf_counter()
    neo_rows = run_neo(cypher, params)
    neo_s = time.perf_counter() - t
    return normalize(pg_rows), normalize(neo_rows), pg_s, neo_s


def trace():
    print('=== 3.3 Inspect account 998 (set A) in both models')
    params = dict(account=SETS['A'][0])
    pg_rows, neo_rows, _, _ = both(TRACE_SQL, TRACE_CYPHER, params)
    cols = ('account_id', 'role', 'customer_id', 'region', 'device_id', 'access_type', 'first_day',
            'last_day', 'observations', 'transfer_id', 'receiver_id', 'occurred_at', 'amount_rwf')
    for engine, rows in (('PostgreSQL JOIN', pg_rows), ('Neo4j MATCH', neo_rows)):
        print(f'-- {engine}')
        for row in rows:
            for col, value in zip(cols, row):
                print(f'   {col:<13}{value}')
            print(f'   {"occurred CAT":<13}{cat(row[11])}')
    print('match:', 'yes' if pg_rows == neo_rows else 'NO')

    print('\n-- repeated payments from account 998 (would collapse into one edge each)')
    pg_rows, neo_rows, _, _ = both(REPEATS_SQL, REPEATS_CYPHER, params)
    print(f'   {"receiver":>9}{"transfers":>11}{"total RWF":>12}  first (CAT)          last (CAT)')
    for receiver, count, total, first, last in pg_rows:
        print(f'   {receiver:>9}{count:>11}{total:>12,}  {cat(first)}  {cat(last)}')
    print('   match:', 'yes' if pg_rows == neo_rows else 'NO', f'({len(pg_rows)} repeated receivers)')
    run_pg("SET work_mem = '512MB'")
    transfers, pairs = run_pg(PAIRS_SQL)[0]
    run_pg('RESET work_mem')
    print(f'\n-- whole month: {transfers:,} transfers between {pairs:,} distinct sender->receiver pairs;'
          f' collapsing would drop {transfers - pairs:,} events')


def q1():
    print('\n=== Q1 Account activity, 09:45 to 10:45 CAT (outgoing, all receiver roles)')
    print(f'{"set":<4}{"account":>8}{"date":>12}{"start":>12}{"end":>12}'
          f'{"PG count":>10}{"PG RWF":>11}{"Neo count":>11}{"Neo RWF":>11}{"match":>7}')
    for name, (account, _, day) in SETS.items():
        params = set_params(name)
        pg_rows, neo_rows, _, _ = both(Q1_SQL, Q1_CYPHER, params)
        (pc, pv), (nc, nv) = pg_rows[0], neo_rows[0]
        print(f'{name:<4}{account:>8}{f"2026-09-{day:02d}":>12}{params["start"]:>12}{params["end"]:>12}'
              f'{pc:>10}{pv:>11,}{nc:>11}{nv:>11,}{"yes" if pg_rows == neo_rows else "NO":>7}')


def q2():
    print('\n=== Q2 Daily activity (CAT days)')
    pg_rows, neo_rows, pg_s, neo_s = both(Q2_SQL, Q2_CYPHER)
    base = min(r[1] for r in pg_rows)
    print(f'{"date":<12}{"transfers":>11}{"total RWF":>18}{"above " + f"{base:,}":>16}')
    for day, count, total in pg_rows:
        print(f'{day.isoformat():<12}{count:>11,}{total:>18,}{count - base:>16,}')
    count = sum(r[1] for r in pg_rows)
    total = sum(r[2] for r in pg_rows)
    print(f'{"TOTAL":<12}{count:>11,}{total:>18,}')
    print(f'\ndays: PostgreSQL {len(pg_rows)}, Neo4j {len(neo_rows)} (expected 30)')
    print(f'PostgreSQL = Neo4j on every day: {"yes" if pg_rows == neo_rows else "NO"}')
    print(f'count reconciles to capture ({CAPTURE_COUNT:,}): {"yes" if count == CAPTURE_COUNT else "NO"}')
    print(f'sum reconciles to capture ({CAPTURE_SUM_RWF:,}): {"yes" if total == CAPTURE_SUM_RWF else "NO"}')
    print(f'single-run time: PostgreSQL {pg_s:.1f}s, Neo4j {neo_s:.1f}s (not a benchmark)')
    plot_q2(pg_rows)


def plot_q2(rows):
    days = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    values = [r[2] / 1e9 for r in rows]
    blue, ink, muted = '#2a78d6', '#0b0b0b', '#52514e'
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for ax, data, label in ((axes[0], counts, 'Transfers per day (count, y-axis not from zero)'),
                            (axes[1], values, 'Value per day (billion RWF, y-axis not from zero)')):
        ax.axvspan(matplotlib.dates.date2num(days[5]) - 0.5, matplotlib.dates.date2num(days[14]) + 0.5,
                   color='#cde2fb', alpha=0.5, linewidth=0)
        ax.plot(days, data, color=blue, linewidth=2, marker='o', markersize=4)
        ax.set_title(label, loc='left', fontsize=11, color=ink)
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('{x:,.0f}'))
    axes[0].text(days[10], min(counts), '6 to 15 Sep', ha='center', va='bottom', color=muted, fontsize=9)
    for ax in axes:
        ax.grid(axis='y', color='#e6e5e0', linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=muted, length=0)
    axes[1].set_xlabel('Date in September 2026 (CAT)', color=muted)
    axes[1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d'))
    axes[1].set_xticks(days)
    fig.suptitle('Q2 Daily transfer activity, September 2026', x=0.06, ha='left', fontsize=13, color=ink)
    fig.tight_layout()
    path = OUTPUT_DIR / 'q2_daily_activity.png'
    fig.savefig(path, dpi=150)
    print(f'chart saved: {path.relative_to(OUTPUT_DIR.parent)}')


def q3():
    print('\n=== Q3 Shared devices with overlapping observation days')
    summary = []
    for name, (account, _, _) in SETS.items():
        pg_rows, neo_rows, _, _ = both(Q3_SQL, Q3_CYPHER, dict(account=account))
        match = pg_rows == neo_rows
        summary.append((name, account, len(pg_rows), len(neo_rows), match))
        print(f'\n-- set {name}, review account {account}: {len(pg_rows)} rows, match {"yes" if match else "NO"}')
        print(f'   {"other":>8}{"device":>8}  {"access_type":<16}{"start":>6}{"end":>5}')
        for other, device, access, start, end in pg_rows:
            print(f'   {other:>8}{device:>8}  {access:<16}{start:>6}{end:>5}')
    print(f'\n{"set":<4}{"account":>8}{"PG rows":>9}{"Neo rows":>10}{"match":>7}')
    for name, account, pc, nc, match in summary:
        print(f'{name:<4}{account:>8}{pc:>9}{nc:>10}{"yes" if match else "NO":>7}')


SECTIONS = dict(trace=trace, q1=q1, q2=q2, q3=q3)

if __name__ == '__main__':
    for section in sys.argv[1:] or SECTIONS:
        SECTIONS[section]()
    close()
