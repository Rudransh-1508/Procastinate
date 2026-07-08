"""Test fixtures — each test gets a fresh isolated SQLite DB."""
import os
import tempfile

import pytest


@pytest.fixture
def fresh_db(monkeypatch):
    """Point the app at a brand-new temp DB and initialize the schema."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    import db.db as dbmod

    # db.py reads its module-global DB_PATH inside get_db(); patch it and
    # drop any cached thread-local connection so it reopens on the temp file.
    monkeypatch.setattr(dbmod, "DB_PATH", tmp.name)
    if hasattr(dbmod._local, "conn"):
        dbmod._local.conn.close()
        del dbmod._local.conn

    dbmod.init_db()
    yield dbmod

    if hasattr(dbmod._local, "conn"):
        dbmod._local.conn.close()
        del dbmod._local.conn
    try:
        os.unlink(tmp.name)
    except OSError:
        pass
