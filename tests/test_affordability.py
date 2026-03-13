"""
Tests for affordability engine: under limit, near limit, projected overspend, goal conflict.
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
from datetime import datetime
import database
from affordability_service import check_affordability


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_under_limit(ensure_db):
    """When within category and total limit, can_afford is True."""
    database.set_limit("food", 500.0, "USD")
    database.set_limit("total", 2000.0, "USD")
    y, m = datetime.now().year, datetime.now().month
    # No or little spend
    result = check_affordability(amount=50.0, category="food", year=y, month=m)
    assert result["can_afford"] is True
    assert any("within" in r.lower() or "limit" in r.lower() for r in result["reasons"])
    assert "recommendation_text" in result
    # Cleanup
    database.delete_limit("food")
    database.delete_limit("total")


def test_over_category_limit(ensure_db):
    """When purchase would exceed category limit, can_afford is False."""
    database.set_limit("food", 100.0, "USD")
    y, m = datetime.now().year, datetime.now().month
    # Add 80 food spend so 50 more = 130 > 100
    for _ in range(4):
        database.save_expense(
            date=f"{y}-{m:02d}-01",
            category="food",
            amount=20.0,
            currency="USD",
            raw_text="aff_test_food",
        )
    try:
        result = check_affordability(amount=50.0, category="food", year=y, month=m)
        assert result["can_afford"] is False
        assert result["budget_impact"] is not None
        assert result["budget_impact"].get("category_over", 0) > 0
    finally:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "aff_test_food":
                database.delete_expense(e["id"])
        database.delete_limit("food")


def test_over_total_limit(ensure_db):
    """When purchase would exceed total limit, can_afford is False."""
    database.set_limit("total", 200.0, "USD")
    y, m = datetime.now().year, datetime.now().month
    for _ in range(5):
        database.save_expense(
            date=f"{y}-{m:02d}-01",
            category="other",
            amount=30.0,
            currency="USD",
            raw_text="aff_test_total",
        )
    try:
        # 150 spent; 100 more = 250 > 200
        result = check_affordability(amount=100.0, category="other", year=y, month=m)
        assert result["can_afford"] is False
        assert result["budget_impact"] is not None
        assert result["budget_impact"].get("total_over", 0) > 0
    finally:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "aff_test_total":
                database.delete_expense(e["id"])
        database.delete_limit("total")


def test_goal_conflict_category_cap(ensure_db):
    """When a category_cap goal exists and purchase would exceed cap, can_afford is False."""
    database.set_limit("food", 1000.0, "USD")  # high limit so not the blocker
    gid = database.create_goal(
        goal_type="category_cap",
        target_amount=80.0,
        current_amount=0.0,
        target_date=None,
        category="food",
        description="Cap food at 80",
        status="active",
    )
    y, m = datetime.now().year, datetime.now().month
    for _ in range(3):
        database.save_expense(
            date=f"{y}-{m:02d}-01",
            category="food",
            amount=20.0,
            currency="USD",
            raw_text="aff_test_cap",
        )
    try:
        # 60 spent + 30 = 90 > 80 cap
        result = check_affordability(amount=30.0, category="food", year=y, month=m)
        assert result["can_afford"] is False
        assert result.get("goal_impact") and result["goal_impact"].get("conflict")
    finally:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "aff_test_cap":
                database.delete_expense(e["id"])
        database.delete_goal(gid)
        database.delete_limit("food")


def test_zero_amount_affordable(ensure_db):
    """Zero or negative amount is always affordable."""
    r = check_affordability(amount=0.0, category="food")
    assert r["can_afford"] is True
    r = check_affordability(amount=-10.0, category="food")
    assert r["can_afford"] is True
