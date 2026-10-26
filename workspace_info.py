"""1.1 Record software/driver versions, hardware, OS and database settings, and test both connections."""
import hashlib
import platform
import subprocess
import sys
from importlib.metadata import version

from config import NEO4J_URI, PG_DSN, ROOT
from db import close, run_neo, run_pg


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def main():
    print('=== machine')
    print(f'CPU            {sh("sysctl", "-n", "machdep.cpu.brand_string")} '
          f'({sh("sysctl", "-n", "hw.ncpu")} cores)')
    print(f'RAM            {int(sh("sysctl", "-n", "hw.memsize")) / 1e9:.1f} GB')
    print(f'OS             macOS {platform.mac_ver()[0]} ({platform.machine()})')

    print('\n=== software and drivers')
    print(f'Python         {sys.version.split()[0]}')
    for package in ('numpy', 'psycopg', 'neo4j', 'matplotlib'):
        print(f'{package:<15}{version(package)}')
    generator = (ROOT / 'mobile_money_generator.py').read_bytes()
    print(f'generator      sha256 {hashlib.sha256(generator).hexdigest()}')

    print(f'\n=== PostgreSQL connection ({PG_DSN})')
    print(run_pg('SELECT version()')[0][0])
    print(run_pg('SELECT current_database(), current_user')[0])
    for name, setting in run_pg("""
            SELECT name, current_setting(name) FROM pg_settings
            WHERE name IN ('TimeZone', 'shared_buffers', 'work_mem', 'maintenance_work_mem',
                           'effective_cache_size', 'max_connections', 'max_parallel_workers_per_gather')
            ORDER BY name"""):
        print(f'  {name:<34}{setting}')
    print('  SHOW timezone ->', run_pg('SHOW timezone')[0][0])

    print(f'\n=== Neo4j connection ({NEO4J_URI})')
    for name, versions, edition in run_neo('CALL dbms.components() YIELD name, versions, edition'):
        print(f'  {name} {versions[0]} {edition}')
    print('  databases:', run_neo('SHOW DATABASES YIELD name, currentStatus, default'))
    for name, value in run_neo("SHOW SETTINGS YIELD name, value "
                               "WHERE name STARTS WITH 'server.memory' RETURN name, value ORDER BY name"):
        print(f'  {name:<52}{value}')
    close()


if __name__ == '__main__':
    main()
