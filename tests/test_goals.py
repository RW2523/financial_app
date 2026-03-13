"""
Tests for goal service: progress, distance to goal, suggested reduction per month/week.
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
from goal_service import (
    create_goal,
    get_goals,
    update_goal_progress,
    distance_to_goal,
    suggested_reduction_per_month,
    suggested_reduction_per_week,
    get_goal_enriched,
)


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_create_goal_and_list(ensure_db):
    """Create a goal and list returns it enriched."""
    gid = database.create_goal(
        goal_type="savings_target",
        target_amount=5000.0,
        current_amount=500.0,
        target_date="2026-12-31",
        category=None,
        description="Emergency fund",
        status="active",
    )
    try:
        goals = get_goals(status="active")
        g = next((x for x in goals if x.get("id") == gid), None)
        assert g is not None
        assert g["goal_type"] == "savings_target"
        assert g["target_amount"] == 5000.0
        assert g["current_amount"] == 500.0
        assert "distance" in g
        assert "suggested_reduction_per_month" in g
        assert "suggested_reduction_per_week" in g
    finally:
        database.delete_goal(gid)


def test_distance_savings_target(ensure_db):
    """Savings target: remaining = target - current; met when current >= target."""
    goal = {"goal_type": "savings_target", "target_amount": 1000.0, "current_amount": 300.0}
    d = distance_to_goal(goal)
    assert d["remaining"] == 700.0
    assert d["met"] is False
    goal["current_amount"] = 1000.0
    d = distance_to_goal(goal)
    assert d["remaining"] == 0
    assert d["met"] is True


def test_distance_category_cap(ensure_db):
    """Category cap: over_amount = current - target when over; met when current <= target."""
    goal = {"goal_type": "category_cap", "target_amount": 200.0, "current_amount": 250.0}
    d = distance_to_goal(goal)
    assert d["over_amount"] == 50.0
    assert d["met"] is False
    goal["current_amount"] = 200.0
    d = distance_to_goal(goal)
    assert d["over_amount"] == 0
    assert d["met"] is True


def test_suggested_reduction_per_month_savings(ensure_db):
    """Suggested per month for savings_target = remaining / months_left."""
    goal = {
        "goal_type": "savings_target",
        "target_amount": 1200.0,
        "current_amount": 0.0,
        "target_date": (datetime.now().year + 1).__str__() + "-01-15",
    }
    per_month = suggested_reduction_per_month(goal)
    assert per_month is not None
    assert per_month > 0
    # Roughly 1200 / 12 or so
    assert 50 <= per_month <= 200


def test_suggested_reduction_with_target_date_past(ensure_db):
    """When target_date is in the past, suggested reduction is None."""
    goal = {
        "goal_type": "savings_target",
        "target_amount": 1000.0,
        "current_amount": 500.0,
        "target_date": "2020-01-01",
    }
    assert suggested_reduction_per_month(goal) is None
    assert suggested_reduction_per_week(goal) is None


def test_update_progress(ensure_db):
    """Update current_amount and verify enriched response."""
    gid = database.create_goal(
        goal_type="savings_target",
        target_amount=1000.0,
        current_amount=0.0,
        target_date=None,
        category=None,
        description="Test",
        status="active",
    )
    try:
        update_goal_progress(gid, 400.0)
        g = get_goal_enriched(gid)
        assert g is not None
        assert g["current_amount"] == 400.0
        d = g["distance"]
        assert d["remaining"] == 600.0
    finally:
        database.delete_goal(gid)
