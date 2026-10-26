"""Section 5: run Q4 to Q7 on both engines, compare the answers and show supporting evidence.

  python run_part2.py            # everything
  python run_part2.py q4 q7      # selected sections: q4, q5, q6, q7
"""
import json
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import OUTPUT_DIR
from db import close, normalize, run_neo, run_pg
from questions import (Q4_FARTHEST_SQL, Q4_PATH_CYPHER, Q4_SQL, Q5_CYPHER, Q5_SQL, Q6_CYPHER, Q6_SQL,
                       Q7_PATH_CHECK_SQL, Q7_SQL, SETS, TRANSFER_DETAILS_SQL, q4_cypher, q7_cypher,
                       q7_params, q7_path_cypher, set_params)

DEPTHS = (4, 6, 8, 10)
BOUNDS = (4, 6)
REGIONS = ('Eastern', 'Kigali', 'Northern', 'Southern', 'Western')


def timed(fn, query, params):
    t = time.perf_counter()
    rows = normalize(fn(query, params))
    return rows, time.perf_counter() - t


def show_transfers(ids):
    rows = run_pg(TRANSFER_DETAILS_SQL, dict(ids=list(ids)))
    print(f'   {"transfer":>9}{"sender":>9}{"receiver":>10}  {"time (CAT)":<20}{"amount RWF":>12}{"% of prev":>11}')
    previous = None
    for transfer, sender, receiver, _, cat, amount in rows:
        share = f'{100 * amount / previous:.2f}%' if previous else ''
        print(f'   {transfer:>9}{sender:>9}{receiver:>10}  {cat:<20}{amount:>12,}{share:>11}')
        previous = amount


def q4():
    print('=== Q4 Ownership and device network (distinct other accounts by owner region)')
    print(f'{"set":<4}{"depth":>6}' + ''.join(f'{r[:4]:>7}' for r in REGIONS)
          + f'{"total":>8}{"PG s":>7}{"Neo s":>7}{"match":>7}')
    totals = {}
    for name, (account, _, _) in SETS.items():
        for depth in DEPTHS:
            params = dict(account=account, depth=depth)
            pg_rows, pg_s = timed(run_pg, Q4_SQL, params)
            neo_rows, neo_s = timed(run_neo, q4_cypher(depth), params)
            by_region = dict(pg_rows)
            total = sum(by_region.values())
            totals.setdefault(name, []).append(total)
            print(f'{name:<4}{depth:>6}' + ''.join(f'{by_region.get(r, 0):>7}' for r in REGIONS)
                  + f'{total:>8}{pg_s:>7.2f}{neo_s:>7.2f}{"yes" if pg_rows == neo_rows else "NO":>7}')
    (OUTPUT_DIR / 'q4_totals.json').write_text(json.dumps(totals))
    plot_q4(totals)

    account = SETS['B'][0]
    target, depth = run_pg(Q4_FARTHEST_SQL, dict(account=account, depth=10))[0]
    path, links = run_neo(Q4_PATH_CYPHER, dict(account=account, target=target))[0]
    print(f'\nsupporting path: set B account {account} to account {target}, '
          f'reached at minimum depth {depth} ({links} links)')
    print('   ' + '  --  '.join(path))


def plot_q4(totals):
    # One panel per set (pairs A/D, B/E, C/F stacked in columns): paired curves are nearly identical
    # and would hide each other on a single chart.
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharex=True)
    order = ('A', 'B', 'C', 'D', 'E', 'F')
    for ax, name in zip(axes.flat, order):
        values = totals[name]
        ax.plot(DEPTHS, values, color='#2a78d6', linewidth=2, marker='o', markersize=6)
        for x, y in zip(DEPTHS, values):
            ax.annotate(f'{y:,}', (x, y), textcoords='offset points', xytext=(0, 7), ha='center',
                        fontsize=8, color='#52514e')
        ax.set_title(f'Set {name} (account {SETS[name][0]})', loc='left', fontsize=10)
        ax.set_ylim(0, max(values) * 1.25)
        ax.set_xticks(DEPTHS)
        ax.grid(axis='y', color='#e6e5e0')
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    fig.supxlabel('Maximum links (OWNS or USED_DEVICE, either direction)', color='#52514e', fontsize=10)
    fig.supylabel('Distinct other accounts reached', color='#52514e', fontsize=10)
    fig.suptitle('Q4 Accounts reached vs depth (count; each panel has its own y-axis)', x=0.02, ha='left', fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / 'q4_count_vs_depth.png'
    fig.savefig(path, dpi=150)
    print(f'chart saved: {path.relative_to(OUTPUT_DIR.parent)}')


def q5():
    print('\n=== Q5 Rapid onward payments (three transfers, four accounts, <= 600 s gaps, 90-105% amounts)')
    print(f'{"set":<4}{"account":>8}{"PG chains":>11}{"Neo chains":>12}{"match":>7}   chains (t1, t2, t3, final receiver)')
    example = None
    for name in SETS:
        params = set_params(name)
        pg_rows, _ = timed(run_pg, Q5_SQL, params)
        neo_rows, _ = timed(run_neo, Q5_CYPHER, params)
        example = example or (pg_rows[0] if pg_rows else None)
        print(f'{name:<4}{params["account"]:>8}{len(pg_rows):>11}{len(neo_rows):>12}'
              f'{"yes" if pg_rows == neo_rows else "NO":>7}   {pg_rows}')
    if example:
        print(f'\nexample chain {example[:3]} ending at account {example[3]}:')
        show_transfers(example[:3])


def q6():
    print('\n=== Q6 Circular payments (3 to 8 transfers back to the review account within its hour)')
    print(f'{"set":<4}{"account":>8}{"PG cycles":>11}{"Neo cycles":>12}{"match":>7}   cycles (transfer ids, length)')
    example = None
    for name in SETS:
        params = set_params(name)
        pg_rows, _ = timed(run_pg, Q6_SQL, params)
        neo_rows, _ = timed(run_neo, Q6_CYPHER, params)
        example = example or (pg_rows[0] if pg_rows else None)
        print(f'{name:<4}{params["account"]:>8}{len(pg_rows):>11}{len(neo_rows):>12}'
              f'{"yes" if pg_rows == neo_rows else "NO":>7}   {pg_rows}')
    if example:
        print(f'\nexample cycle {example[0]} (length {example[1]}):')
        show_transfers(example[0])


def q7():
    print('\n=== Q7 Shortest transfer connection (persons only, directed, any time order)')
    print(f'{"set":<4}{"account":>8}{"destination":>12}{"bound":>6}{"PG length":>11}{"Neo length":>12}'
          f'{"PG s":>8}{"Neo s":>7}{"match":>7}')
    found = []
    for name in SETS:
        base = set_params(name)
        for bound in BOUNDS:
            params = q7_params(base, bound)
            pg_rows, pg_s = timed(run_pg, Q7_SQL, params)
            neo_rows, neo_s = timed(run_neo, q7_cypher(bound), params)
            length = pg_rows[0][0]
            shown = 'none' if length is None else length
            neo_shown = 'none' if neo_rows[0][0] is None else neo_rows[0][0]
            print(f'{name:<4}{base["account"]:>8}{base["destination"]:>12}{bound:>6}{shown:>11}{neo_shown:>12}'
                  f'{pg_s:>8.2f}{neo_s:>7.2f}{"yes" if pg_rows == neo_rows else "NO":>7}')
            if length is not None:
                found.append((name, bound, params, length))

    print('\n-- one Neo4j path per successful case, checked against PostgreSQL rows')
    for name, bound, params, length in found:
        accounts, transfers = run_neo(q7_path_cypher(bound), params)[0]
        checks = run_pg(Q7_PATH_CHECK_SQL, dict(accounts=accounts, transfers=transfers))
        ok = (len(transfers) == length and len(checks) == length
              and all(c[1] is not None and c[4] == 'person' and c[5] == 'person' and c[6] for c in checks))
        print(f'{name} bound {bound}: accounts {accounts}')
        print(f'   transfers {transfers}  length {len(transfers)} = {length}: '
              f'events exist, direction in order, all persons: {"yes" if ok else "NO"}')


SECTIONS = dict(q4=q4, q5=q5, q6=q6, q7=q7)

if __name__ == '__main__':
    for section in sys.argv[1:] or SECTIONS:
        SECTIONS[section]()
    close()
