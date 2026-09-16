"""Small transactional state store and immutable, atomic JSON receipts."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
        ).encode()
        + b"\n"
    )
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.link(temporary, path)  # atomic publication; never overwrite
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


@contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "state.sqlite"
        with self.connect() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);"
                "CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, time TEXT, kind TEXT, value TEXT);"
            )

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value, *, event=None):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO state VALUES (?,?)",
                (key, json.dumps(value, allow_nan=False)),
            )
            if event:
                db.execute(
                    "INSERT INTO events(time,kind,value) VALUES(?,?,?)",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        event,
                        json.dumps(value, allow_nan=False),
                    ),
                )

    def entries(self):
        with self.connect() as db:
            return {
                key: json.loads(value)
                for key, value in db.execute("SELECT key,value FROM state ORDER BY key")
            }
