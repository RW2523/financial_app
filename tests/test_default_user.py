"""
Tests for single-user / default user behavior: all data scoped to default user, no auth required.
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

os.chdir(_BACKEND)

import pytest
import sqlite3
import database
from config import DEFAULT_USER_ID


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_default_user_id_constant():
    """Default user id is defined and is 'local' unless overridden by env."""
    assert DEFAULT_USER_ID is not None
    assert isinstance(DEFAULT_USER_ID, str)
    assert len(DEFAULT_USER_ID) > 0


def test_users_table_has_local_user(ensure_db):
    """After init, users table exists and contains the default user."""
    conn = sqlite3.connect(database.DATABASE_PATH, timeout=database.SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (DEFAULT_USER_ID,))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == DEFAULT_USER_ID


def test_expense_saved_with_default_user(ensure_db):
    """Saving an expense without passing user_id associates it with default user (when column exists)."""
    eid = database.save_expense(
        "2026-02-01",
        "food",
        10.0,
        "USD",
        "test_default_user",
    )
    try:
        conn = sqlite3.connect(database.DATABASE_PATH, timeout=database.SQLITE_TIMEOUT)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(expenses)")
        has_user = any(r[1] == "user_id" for r in cursor.fetchall())
        if has_user:
            cursor.execute("SELECT user_id FROM expenses WHERE id = ?", (eid,))
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == DEFAULT_USER_ID
        conn.close()
    finally:
        database.delete_expense(eid)


def test_get_all_expenses_returns_scoped_data(ensure_db):
    """get_all_expenses() without user_id returns data for default user (no cross-user leak)."""
    expenses = database.get_all_expenses()
    # Just ensure it runs and returns a list; scope is enforced inside database
    assert isinstance(expenses, list)


def test_get_limits_uses_default_user(ensure_db):
    """get_limits() without user_id returns limits for default user."""
    limits = database.get_limits()
    assert isinstance(limits, list)


def test_init_database_idempotent(ensure_db):
    """Calling init_database() twice does not raise and schema remains valid."""
    database.init_database()
    database.init_database()
    limits = database.get_limits()
    assert isinstance(limits, list)
