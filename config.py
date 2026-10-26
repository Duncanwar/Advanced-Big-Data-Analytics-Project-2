"""Connection settings shared by every script.

Values come from environment variables or a local .env file (not committed).
Copy .env.example to .env and fill in your own password.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
IMPORT_DIR = ROOT / 'import'
OUTPUT_DIR = ROOT / 'outputs'

_env = ROOT / '.env'
if _env.exists():
    for line in _env.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())

PG_DSN = os.environ.get('PG_DSN', 'dbname=momo')
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'change-me')
NEO4J_DATABASE = 'neo4j'
