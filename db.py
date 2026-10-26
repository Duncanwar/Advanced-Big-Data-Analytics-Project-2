"""Persistent PostgreSQL and Neo4j connections with run_pg / run_neo wrappers.

Both wrappers return every result row as a tuple of plain Python values, so the
two engines' answers can be normalized, sorted and compared exactly.
"""
import datetime as dt
from decimal import Decimal

import psycopg
from neo4j import GraphDatabase
from neo4j.time import Date, DateTime

from config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, PG_DSN

_pg = None
_neo = None


def pg():
    global _pg
    if _pg is None:
        _pg = psycopg.connect(PG_DSN, autocommit=True)
    return _pg


def neo():
    global _neo
    if _neo is None:
        _neo = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _neo.verify_connectivity()
    return _neo


def run_pg(query, params=None):
    with pg().cursor() as cur:
        cur.execute(query, params)
        if cur.description is None:  # SET, DDL and other statements without rows
            return []
        return [tuple(row) for row in cur.fetchall()]


def run_neo(query, params=None):
    with neo().session(database=NEO4J_DATABASE) as session:
        return [tuple(record.values()) for record in session.run(query, params or {})]


def normalize_value(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (Date, DateTime)):
        return value.to_native()
    if isinstance(value, list):
        return tuple(normalize_value(v) for v in value)
    if isinstance(value, dt.datetime):
        return value
    return value


def normalize(rows):
    return sorted(tuple(normalize_value(v) for v in row) for row in rows)


def close():
    global _pg, _neo
    if _pg is not None:
        _pg.close()
        _pg = None
    if _neo is not None:
        _neo.close()
        _neo = None
