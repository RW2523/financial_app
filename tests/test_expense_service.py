"""
Unit tests for expense_service facade: save, get, list with current user context.
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
import database
import expense_service as svc
from context import set_current_user_id
from config import DEFAULT_USER_ID


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()
    set_current_user_id(None)


def test_expense_service_save_expense_returns_id(ensure_db):
    eid = svc.save_expense("2026-03-01", "food", 12.0, "USD", "expense_service_test")
    try:
        assert isinstance(eid, int)
        assert eid > 0
    finally:
        database.delete_expense(eid)


def test_expense_service_get_expense(ensure_db):
    eid = svc.save_expense("2026-03-02", "transport", 20.0, "USD", "expense_service_get_test")
    try:
        row = svc.get_expense(eid)
        assert row is not None
        assert row["category"] == "transport"
        assert float(row["amount"]) == 20.0
    finally:
        database.delete_expense(eid)


def test_expense_service_get_all_expenses_returns_list(ensure_db):
    data = svc.get_all_expenses()
    assert isinstance(data, list)


def test_expense_service_get_monthly_expenses_returns_list(ensure_db):
    data = svc.get_monthly_expenses(2026, 3)
    assert isinstance(data, list)


def test_expense_service_get_expenses_for_review_returns_list(ensure_db):
    data = svc.get_expenses_for_review(confidence_threshold=0.6)
    assert isinstance(data, list)


def test_expense_service_delete_expense(ensure_db):
    eid = svc.save_expense("2026-03-03", "other", 1.0, "USD", "expense_service_delete_test")
    ok = svc.delete_expense(eid)
    assert ok is True
    assert svc.get_expense(eid) is None
