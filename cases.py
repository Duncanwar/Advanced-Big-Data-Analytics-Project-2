"""The 61 comparison cases (Q1 6, Q2 1, Q3 6, Q4 24, Q5 6, Q6 6, Q7 12) and the 21 timed cases."""
from dataclasses import dataclass, field

from questions import (Q1_CYPHER, Q1_SQL, Q2_CYPHER, Q2_SQL, Q3_CYPHER, Q3_SQL, Q4_SQL, Q5_CYPHER, Q5_SQL,
                       Q6_CYPHER, Q6_SQL, Q7_SQL, Q7_SQL_BIDIRECTIONAL, SETS, q4_cypher, q7_cypher,
                       q7_params, set_params)

Q7_VERSIONS = dict(naive=Q7_SQL, bidir=Q7_SQL_BIDIRECTIONAL)


@dataclass
class Case:
    case_id: str
    question: str
    label: str
    sql: str
    cypher: str
    params: dict = field(default_factory=dict)


def all_cases(q7_version='naive'):
    cases = []
    for name in SETS:
        cases.append(Case(f'Q1-{name}', 'Q1', f'set {name}', Q1_SQL, Q1_CYPHER, set_params(name)))
    cases.append(Case('Q2-month', 'Q2', 'full month', Q2_SQL, Q2_CYPHER))
    for name in SETS:
        cases.append(Case(f'Q3-{name}', 'Q3', f'set {name}', Q3_SQL, Q3_CYPHER, set_params(name)))
    for name in SETS:
        for depth in (4, 6, 8, 10):
            cases.append(Case(f'Q4-{name}-d{depth}', 'Q4', f'set {name} depth {depth}', Q4_SQL, q4_cypher(depth),
                              dict(set_params(name), depth=depth)))
    for name in SETS:
        cases.append(Case(f'Q5-{name}', 'Q5', f'set {name}', Q5_SQL, Q5_CYPHER, set_params(name)))
    for name in SETS:
        cases.append(Case(f'Q6-{name}', 'Q6', f'set {name}', Q6_SQL, Q6_CYPHER, set_params(name)))
    for name in SETS:
        for bound in (4, 6):
            cases.append(Case(f'Q7-{name}-b{bound}', 'Q7', f'set {name} bound {bound}', Q7_VERSIONS[q7_version],
                              q7_cypher(bound), q7_params(set_params(name), bound)))
    return cases


TIMED = ['Q1-B', 'Q1-E', 'Q2-month', 'Q3-B', 'Q3-E',
         *[f'Q4-{s}-d{d}' for s in 'BE' for d in (4, 6, 8, 10)],
         'Q5-B', 'Q5-E', 'Q6-B', 'Q6-E',
         *[f'Q7-{s}-b{b}' for s in 'BE' for b in (4, 6)]]


def timed_cases(q7_version='naive'):
    by_id = {c.case_id: c for c in all_cases(q7_version)}
    return [by_id[i] for i in TIMED]
