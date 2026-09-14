"""SQLite run ledger. Connections close after every operation."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


@contextmanager
def connection():
    path = Path(os.getenv("EVALUATION_DB_PATH", "data/evaluations.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE IF NOT EXISTS runs (sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO schema_versions VALUES (1)")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save(record):
    record = {**record, "run_id": str(uuid4())}
    with connection() as conn:
        conn.execute("INSERT INTO runs(run_id, payload) VALUES (?, ?)", (record["run_id"], json.dumps(record, allow_nan=False)))
    return record


def records():
    with connection() as conn:
        return [json.loads(row[0]) for row in conn.execute("SELECT payload FROM runs ORDER BY sequence DESC")]


def get(run_id):
    with connection() as conn:
        row = conn.execute("SELECT payload FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None
