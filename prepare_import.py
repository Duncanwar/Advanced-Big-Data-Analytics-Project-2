"""3.2 Make temporary Neo4j import copies of the captured CSVs with typed headers."""
import csv
import shutil
import time

from config import DATA_DIR, IMPORT_DIR

HEADERS = {
    'customers.csv': ('customers.csv', 'customer_id:ID(Customer),region:string'),
    'accounts.csv': ('accounts.csv', 'account_id:ID(Account),:IGNORE,role:string'),
    'devices.csv': ('devices.csv', 'device_id:ID(Device),access_type:string'),
    'account_devices.csv': ('used_device.csv',
                            ':START_ID(Account),:END_ID(Device),first_day:int,last_day:int,observations:int'),
    'transfers.csv': ('transfers.csv',
                      'transfer_id:long,:START_ID(Account),:END_ID(Account),occurred_at:long,amount_rwf:int'),
}
OWNS_HEADER = ':START_ID(Customer),:END_ID(Account)'


def retype(source, target, header):
    with open(source, newline='') as src, open(target, 'w', newline='') as dst:
        src.readline()
        dst.write(header + '\n')
        shutil.copyfileobj(src, dst, 16 * 1024 * 1024)


def derive_owns(accounts, target):
    rows = 0
    with open(accounts, newline='') as src, open(target, 'w', newline='') as dst:
        reader = csv.DictReader(src)
        dst.write(OWNS_HEADER + '\n')
        writer = csv.writer(dst)
        for row in reader:
            writer.writerow((row['customer_id'], row['account_id']))
            rows += 1
    return rows


def main():
    IMPORT_DIR.mkdir(exist_ok=True)
    start = time.perf_counter()
    for source, (target, header) in HEADERS.items():
        t = time.perf_counter()
        retype(DATA_DIR / source, IMPORT_DIR / target, header)
        print(f'{source:<20} -> import/{target:<18} {time.perf_counter() - t:6.1f}s  header: {header}')
    t = time.perf_counter()
    rows = derive_owns(DATA_DIR / 'accounts.csv', IMPORT_DIR / 'owns.csv')
    print(f'{"accounts.csv":<20} -> import/{"owns.csv":<18} {time.perf_counter() - t:6.1f}s  '
          f'header: {OWNS_HEADER}  ({rows:,} rows)')
    print(f'\nprepared {len(HEADERS) + 1} import files in {time.perf_counter() - start:.1f}s')
    for path in sorted(IMPORT_DIR.glob('*.csv')):
        with open(path) as f:
            print(f'  {path.name:<18} {path.stat().st_size / 1e6:8.1f} MB  first lines: '
                  f'{f.readline().strip()} | {f.readline().strip()}')


if __name__ == '__main__':
    main()
