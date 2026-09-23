"""Portable CSV exports, typed SQLite tables, SQL views and content hashes."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path


def canonical(value):
    """Stabilize float serialization across supported Python/SQLite versions."""
    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    return value


def write_csv(path, rows):
    """Write stable columns and UTF-8; nulls serialize as blank cells."""
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(canonical(rows))


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical(obj), indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def store_tables(out, tables, sql_path):
    """Create fresh derived database transactionally; export each analytical view too."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    db = out/'aeroplan.sqlite'
    temporary = out/'aeroplan.build.sqlite'
    if temporary.exists():
        temporary.unlink()
    with sqlite3.connect(temporary) as con:
        for name, rows in tables.items():
            rows = canonical(rows)
            if not rows:
                continue
            columns = list(rows[0])
            types = []
            for c in columns:
                values = [r[c] for r in rows if r[c] is not None]
                types.append('INTEGER' if values and all(isinstance(v, int) for v in values)
                             else 'REAL' if values and all(isinstance(v, (int, float)) for v in values) else 'TEXT')
            schema = ','.join(f'"{c}" {t}' for c, t in zip(columns, types))
            con.execute(f'CREATE TABLE "{name}" ({schema})')
            placeholders = ','.join('?' for _ in columns)
            con.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})',
                            [[r[c] for c in columns] for r in rows])
            write_csv(out/'csv'/f'{name}.csv', rows)
        for table, columns in [('production_plan', 'scenario,week,product'),
                               ('capacity_execution', 'scenario,week'),
                               ('material_balance', 'scenario,week,component'),
                               ('order_fulfillment', 'scenario,order_id'),
                               ('demand_forecast', 'vintage_week,week,product')]:
            con.execute(f'CREATE UNIQUE INDEX idx_{table} ON {table}({columns})')
        con.executescript(Path(sql_path).read_text(encoding='utf-8'))
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name").fetchall():
            cur = con.execute(f'SELECT * FROM {name}')
            write_csv(out/'csv'/f'{name}.csv', [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()])
        integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError(integrity)
    temporary.replace(db)
    return db


def manifest(out, config):
    """Hash deterministic data exports, excluding SQLite binary implementation details."""
    out = Path(out)
    hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(out.rglob('*.csv'))}
    write_json(out/'manifest.json', {'config': config, 'sha256': hashes})
