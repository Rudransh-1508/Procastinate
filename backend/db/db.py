"""SQLite connection helpers and ID generation.

A single connection is shared per-thread. Rows come back as sqlite3.Row so
callers can use dict-style access (row["col"]).
"""
import sqlite3
import threading
import uuid
import hashlib
import re
from pathlib import Path

from config import DB_PATH

_local = threading.local()
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db() -> sqlite3.Connection:
    """Return a thread-local SQLite connection with Row factory + FK enforcement."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create all tables from schema.sql. Idempotent."""
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text())
    db.commit()


def generate_id() -> str:
    """Random UUID4 hex string."""
    return uuid.uuid4().hex


def generate_id_from_title(title: str, user_id: str) -> str:
    """Deterministic ID derived from (user_id, title) for plaintext task dedup.

    Namespaced by user so two users with an identically-titled task in their
    plaintext file never collide on the same primary key.
    """
    slug = re.sub(r"\s+", "-", title.strip().lower())
    digest = hashlib.sha1(f"{user_id}:{slug}".encode("utf-8")).hexdigest()[:12]
    return f"pt-{digest}"
