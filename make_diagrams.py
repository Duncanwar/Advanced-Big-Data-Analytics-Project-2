"""Draw the 2.1 relational schema and the 3.1 graph schema as PNG figures for the report."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from config import OUTPUT_DIR

BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, MUTED, LINE, PAPER = '#0b0b0b', '#52514e', '#9a9893', '#fcfcfb'
ROW = 0.42


def table(ax, x, y, name, columns, width=3.6):
    """Draw a table box with its top-left corner at (x, y); return {column: (left, right, y)} anchors."""
    height = ROW * (len(columns) + 1)
    ax.add_patch(FancyBboxPatch((x, y - height), width, height, boxstyle='round,pad=0,rounding_size=0.08',
                                facecolor=PAPER, edgecolor=LINE, linewidth=1.2))
    ax.add_patch(FancyBboxPatch((x, y - ROW), width, ROW, boxstyle='round,pad=0,rounding_size=0.08',
                                facecolor=BLUE, edgecolor=BLUE, linewidth=1.2))
    ax.text(x + 0.15, y - ROW / 2, name, color='white', fontsize=11, fontweight='bold', va='center')
    anchors = {}
    for i, (col, typ, key) in enumerate(columns):
        cy = y - ROW * (i + 1.5)
        ax.text(x + 0.15, cy, key, color=ORANGE if 'FK' in key else BLUE, fontsize=8, fontweight='bold', va='center')
        ax.text(x + 0.75, cy, col, color=INK, fontsize=9.5, va='center')
        ax.text(x + width - 0.12, cy, typ, color=MUTED, fontsize=8.5, va='center', ha='right')
        anchors[col] = (x, x + width, cy)
    return anchors


def link(ax, start, end, rad=0.0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=12, color=MUTED,
                                 linewidth=1.2, connectionstyle=f'arc3,rad={rad}'))


def relational():
    fig, ax = plt.subplots(figsize=(12, 7.2))
    customers = table(ax, 0.2, 7.0, 'customers', [('customer_id', 'INTEGER', 'PK'), ('region', 'TEXT', '')])
    accounts = table(ax, 4.6, 7.0, 'accounts', [('account_id', 'INTEGER', 'PK'), ('customer_id', 'INTEGER', 'FK'),
                                                ('role', 'TEXT', '')])
    devices = table(ax, 9.0, 7.0, 'devices', [('device_id', 'INTEGER', 'PK'), ('access_type', 'TEXT', '')])
    usage = table(ax, 8.6, 3.9, 'account_devices', [('account_id', 'INTEGER', 'PK FK'), ('device_id', 'INTEGER', 'PK FK'),
                                                     ('first_day', 'SMALLINT', ''), ('last_day', 'SMALLINT', ''),
                                                     ('observations', 'INTEGER', '')], width=4.0)
    transfers = table(ax, 2.2, 3.9, 'transfers', [('transfer_id', 'BIGINT', 'PK'), ('sender_id', 'INTEGER', 'FK'),
                                                  ('receiver_id', 'INTEGER', 'FK'), ('occurred_at', 'BIGINT', ''),
                                                  ('amount_rwf', 'INTEGER', '')], width=4.0)
    # FK -> PK arrows (ownership, device use, both transfer endpoints)
    link(ax, (accounts['customer_id'][0], accounts['customer_id'][2]),
         (customers['customer_id'][1], customers['customer_id'][2]))
    link(ax, (usage['account_id'][0], usage['account_id'][2]), (accounts['account_id'][1], accounts['account_id'][2]), 0.25)
    link(ax, (11.9, 3.9), (11.9, devices['access_type'][2] - ROW / 2))
    accounts_bottom = accounts['role'][2] - ROW / 2
    link(ax, (transfers['sender_id'][1], transfers['sender_id'][2]), (6.9, accounts_bottom))
    link(ax, (transfers['receiver_id'][1], transfers['receiver_id'][2]), (7.5, accounts_bottom))
    notes = ['All columns NOT NULL.  Arrows point from foreign key to the referenced primary key.',
             'CHECK amount_rwf > 0;  CHECK observations > 0;  CHECK 0 <= first_day <= last_day <= 29 (day 0 = 1 Sep 2026 CAT).',
             'occurred_at = Unix epoch seconds;  amount_rwf = whole Rwandan francs.']
    for i, note in enumerate(notes):
        ax.text(0.2, 0.75 - i * 0.33, note, color=MUTED, fontsize=9)
    ax.set_xlim(0, 13); ax.set_ylim(0, 7.3); ax.axis('off')
    ax.set_title('PostgreSQL schema (2.1)', loc='left', fontsize=13, color=INK)
    fig.tight_layout()
    path = OUTPUT_DIR / 'schema_postgres.png'
    fig.savefig(path, dpi=200, facecolor='white')
    return path


def node(ax, x, y, label, props, color):
    ax.add_patch(FancyBboxPatch((x - 1.3, y - 0.55), 2.6, 1.1, boxstyle='round,pad=0,rounding_size=0.5',
                                facecolor=color, edgecolor=color))
    ax.text(x, y + 0.17, f':{label}', color='white', fontsize=12, fontweight='bold', ha='center', va='center')
    ax.text(x, y - 0.22, props, color='white', fontsize=8.5, ha='center', va='center')


def edge(ax, start, end, label, props):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=16, color=MUTED, linewidth=1.6))
    mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    ax.text(mx, my + 0.15, label, color=INK, fontsize=10.5, fontweight='bold', ha='center', va='bottom')
    ax.text(mx, my - 0.15, props, color=MUTED, fontsize=8, ha='center', va='top')


def graph():
    fig, ax = plt.subplots(figsize=(12, 6))
    node(ax, 1.8, 4.0, 'Customer', '{customer_id:int, region}', AQUA)
    node(ax, 6.5, 4.0, 'Account', '{account_id:int, role}', BLUE)
    node(ax, 11.2, 4.0, 'Device', '{device_id:int, access_type}', ORANGE)
    edge(ax, (3.1, 4.0), (5.2, 4.0), ':OWNS', '248,000; one per account')
    edge(ax, (7.8, 4.0), (9.9, 4.0), ':USED_DEVICE', '{first_day, last_day,\nobservations:int}')
    # Self-loop below the Account node: TRANSFER goes from one Account to another Account.
    ax.add_patch(FancyArrowPatch((5.7, 3.45), (7.3, 3.45), arrowstyle='-|>', mutation_scale=16, color=MUTED,
                                 linewidth=1.6, connectionstyle='arc3,rad=1.2'))
    ax.text(6.5, 1.85, ':TRANSFER  (Account to Account, one relationship per event)', color=INK, fontsize=10.5,
            fontweight='bold', ha='center')
    ax.text(6.5, 1.5, '{transfer_id:long, occurred_at:long, amount_rwf:int}; 20,003,300 kept, repeats preserved',
            color=MUTED, fontsize=8.5, ha='center')
    ax.text(0.3, 0.3, 'Counts: 228,000 Customer, 248,000 Account, 228,600 Device nodes; 285,600 USED_DEVICE. '
            'Totals 704,600 nodes, 20,536,900 relationships.', color=MUTED, fontsize=9)
    ax.set_xlim(0, 13); ax.set_ylim(0, 5.2); ax.axis('off')
    ax.set_title('Neo4j graph schema (3.1)', loc='left', fontsize=13, color=INK)
    fig.tight_layout()
    path = OUTPUT_DIR / 'schema_graph.png'
    fig.savefig(path, dpi=200, facecolor='white')
    return path


def cycle_a():
    """8.1 Set A Q6 cycle: four transfers in two minutes back to account 998."""
    fig, ax = plt.subplots(figsize=(11, 5))
    spots = {998: (2, 3.6), 8917: (6.5, 3.6), 16836: (11, 3.6), 24755: (6.5, 0.9)}
    regions = {998: 'Kigali', 8917: 'Kigali', 16836: 'Northern', 24755: 'Northern'}
    for acc, (x, y) in spots.items():
        color = ORANGE if acc == 998 else BLUE
        ax.add_patch(FancyBboxPatch((x - 1.1, y - 0.42), 2.2, 0.84, boxstyle='round,pad=0,rounding_size=0.25',
                                    facecolor=color, edgecolor=color))
        ax.text(x, y + 0.1, f'Account {acc}', color='white', fontsize=11, fontweight='bold', ha='center', va='center')
        ax.text(x, y - 0.2, regions[acc] + (' (review)' if acc == 998 else ''), color='white', fontsize=8.5,
                ha='center', va='center')
    hops = [(998, 8917, '20000001  10:00:00\n200,000 RWF', (0, 0.25)),
            (8917, 16836, '20000002  10:00:40\n196,000 RWF (98%)', (0, 0.25)),
            (16836, 24755, '20000003  10:01:20\n192,080 RWF (98%)', (1.3, 0.1)),
            (24755, 998, '20000004  10:02:00\n188,238 RWF (98%)', (-1.3, 0.1))]
    for a, b, label, (dx, dy) in hops:
        (x1, y1), (x2, y2) = spots[a], spots[b]
        start = (x1 + (1.1 if x2 > x1 else -1.1 if x2 < x1 else 0), y1 - (0.42 if y2 < y1 else 0))
        end = (x2 - (1.1 if x2 > x1 else -1.1 if x2 < x1 else 0), y2 + (0.42 if y2 < y1 else 0))
        if y1 != y2:
            start, end = (x1, y1 - 0.42) if y2 < y1 else (x1 - 1.1, y1 + 0.3), (x2 + 1.1, y2) if y2 < y1 else (x2, y2 - 0.42)
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=16, color=MUTED, linewidth=1.6))
        ax.text((start[0] + end[0]) / 2 + dx, (start[1] + end[1]) / 2 + dy, label, color=INK, fontsize=9,
                ha='center', va='bottom')
    ax.text(0.2, -0.15, 'Q6 set A, 6 Sep 2026 (CAT): 4 transfers, 120 seconds, each 98% of the previous amount; '
            'times are CAT; arrows follow payment direction.', color=MUTED, fontsize=9)
    ax.set_xlim(0, 13); ax.set_ylim(-0.4, 4.6); ax.axis('off')
    ax.set_title('Transfer cycle from review account 998 (Q5 chain = first three transfers)', loc='left', fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / 'diagram_cycle_A.png'
    fig.savefig(path, dpi=200, facecolor='white')
    return path


def network_a():
    """8.1 Set A ownership and device links around account 998 (Q3 evidence)."""
    fig, ax = plt.subplots(figsize=(12, 5.6))

    def box(x, y, text, sub, color, w=2.3):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - 0.4), w, 0.8, boxstyle='round,pad=0,rounding_size=0.25',
                                    facecolor=color, edgecolor=color))
        ax.text(x, y + 0.1, text, color='white', fontsize=10, fontweight='bold', ha='center', va='center')
        ax.text(x, y - 0.2, sub, color='white', fontsize=8, ha='center', va='center')

    def arrow(p, q, label=''):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=13, color=MUTED, linewidth=1.3))
        if label:
            ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.08, label, color=MUTED, fontsize=8, ha='center')

    box(1.6, 4.4, 'Customer 998', 'Kigali', AQUA)
    box(1.6, 2.6, 'Account 998', 'person (review)', ORANGE)
    box(4.0, 2.6, 'Account 220998', 'person, 2nd wallet', BLUE)
    box(3.0, 0.7, 'Device 998', 'handset, days 0-29', '#6250d6')
    arrow((1.6, 4.0), (1.6, 3.0), 'OWNS')
    arrow((2.2, 4.0), (3.7, 3.0), 'OWNS')
    arrow((1.8, 2.2), (2.6, 1.1), 'USED_DEVICE')
    arrow((3.8, 2.2), (3.4, 1.1), 'USED_DEVICE')

    box(9.6, 0.7, 'Device 228001', 'handset, days 0-29', '#6250d6')
    arrow((2.6, 2.3), (8.5, 0.9), 'USED_DEVICE')
    for x, acc, region in ((7.6, 8917, 'Kigali'), (10.2, 16836, 'Northern'), (12.8, 24755, 'Northern (destination)')):
        box(x - 0.6, 4.4, f'Customer {acc}', region, AQUA, w=2.4)
        box(x - 0.6, 2.6, f'Account {acc}', 'person', BLUE, w=2.4)
        arrow((x - 0.6, 4.0), (x - 0.6, 3.0), 'OWNS')
        arrow((x - 0.6, 2.2), (9.6 + (x - 10.2) * 0.35, 1.1), '')
    ax.text(0.3, -0.25, 'Same phone, same owner: 998 and 220998 (ordinary second wallet).   Shared handset 228001: '
            'four different owners in two regions, all observed days 0-29.', color=MUTED, fontsize=9)
    ax.set_xlim(0, 13.7); ax.set_ylim(-0.5, 5.0); ax.axis('off')
    ax.set_title('Ownership and device links around review account 998 (Q3)', loc='left', fontsize=12)
    fig.tight_layout()
    path = OUTPUT_DIR / 'diagram_network_A.png'
    fig.savefig(path, dpi=200, facecolor='white')
    return path


if __name__ == '__main__':
    print(relational())
    print(graph())
    print(cycle_a())
    print(network_a())
