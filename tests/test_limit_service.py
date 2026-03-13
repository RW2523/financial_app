"""
Unit tests for limit_service facade: get_limits, set_limit, delete_limit with current user.
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
import limit_service as svc
from context import set_current_user_id


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()
    set_current_user_id(None)


def test_limit_service_set_and_get_limits(ensure_db):
    svc.set_limit("food", 400.0, "USD")
    try:
        limits = svc.get_limits()
        assert isinstance(limits, list)
        food = next((l for l in limits if l.get("category") == "food"), None)
        assert food is not None
        assert float(food["amount"]) == 400.0
    finally:
        svc.delete_limit("food")


def test_limit_service_delete_limit(ensure_db):
    svc.set_limit("test_cat", 100.0)
    assert any(l.get("category") == "test_cat" for l in svc.get_limits())
    ok = svc.delete_limit("test_cat")
    assert ok is True
    assert not any(l.get("category") == "test_cat" for l in svc.get_limits())
