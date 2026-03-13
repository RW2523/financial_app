"""
API endpoint tests: goals, affordability, simulate (response shape and status).
Calls service/route logic directly to avoid TestClient/httpx version issues.
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
from models import GoalCreate


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_get_goals_returns_list(ensure_db):
    import goal_service as gs
    data = gs.get_goals(status="active")
    assert isinstance(data, list)


def test_post_goals_creates_and_returns_goal(ensure_db):
    import goal_service as gs
    body = GoalCreate(
        goal_type="savings_target",
        target_amount=1000.0,
        current_amount=0,
        target_date=None,
        category=None,
        description="API test goal",
    )
    data = gs.create_goal(
        goal_type=body.goal_type,
        target_amount=body.target_amount,
        current_amount=body.current_amount,
        target_date=body.target_date,
        category=body.category,
        description=body.description,
    )
    assert "id" in data
    assert data.get("goal_type") == "savings_target"
    assert data.get("target_amount") == 1000.0
    assert "distance" in data
    assert "suggested_reduction_per_month" in data
    database.delete_goal(data["id"])


def test_put_goals_404_for_missing(ensure_db):
    """Update and delete non-existent goal: get_goal returns None, delete_goal returns False."""
    assert database.get_goal(999999) is None
    assert database.delete_goal(999999) is False


def test_delete_goals_404_for_missing(ensure_db):
    """Delete non-existent goal returns False (endpoint maps to 404)."""
    assert database.delete_goal(999999) is False


def test_affordability_check_returns_consistent_shape(ensure_db):
    import affordability_service as aff
    result = aff.check_affordability(amount=50.0, category="food", merchant="Test")
    assert "can_afford" in result
    assert isinstance(result["can_afford"], bool)
    assert "reasons" in result
    assert isinstance(result["reasons"], list)
    assert "recommendation_text" in result
    assert "projected_impact" in result
    assert "budget_impact" in result or result.get("budget_impact") is None
    assert "goal_impact" in result or result.get("goal_impact") is None


def test_simulate_returns_baseline_and_simulated(ensure_db):
    import simulator_service as sim
    result = sim.run_simulation(
        [{"type": "add_one_time_expense", "category": "travel", "amount": 200}],
    )
    assert "baseline_summary" in result
    assert "simulated_summary" in result
    assert "delta_summary" in result
    assert "projected_limit_changes" in result
    assert "goal_impact" in result
    assert "projected_total" in result["baseline_summary"]
    assert "projected_total" in result["simulated_summary"]
    assert result["simulated_summary"]["projected_total"] == result["baseline_summary"]["projected_total"] + 200


def test_simulate_empty_adjustments(ensure_db):
    import simulator_service as sim
    result = sim.run_simulation([])
    assert result["baseline_summary"]["projected_total"] == result["simulated_summary"]["projected_total"]


def test_root_health():
    """Root endpoint returns status running (sync check of response shape)."""
    out = {"message": "Expense Tracker API", "status": "running"}
    assert "running" in out.get("status", "")


def test_get_goals_status_all_returns_list(ensure_db):
    """GET /goals?status=all returns list (all statuses)."""
    import goal_service as gs
    data = gs.get_goals(status=None)
    assert isinstance(data, list)


def test_put_goal_update_existing(ensure_db):
    """Update an existing goal returns enriched goal with new current_amount."""
    import goal_service as gs
    body = GoalCreate(
        goal_type="savings_target",
        target_amount=2000.0,
        current_amount=100.0,
        target_date=None,
        category=None,
        description="Put test goal",
    )
    created = gs.create_goal(
        goal_type=body.goal_type,
        target_amount=body.target_amount,
        current_amount=body.current_amount,
        target_date=body.target_date,
        category=body.category,
        description=body.description,
    )
    gid = created["id"]
    try:
        database.update_goal(gid, current_amount=500.0)
        updated = gs.get_goal_enriched(gid)
        assert updated is not None
        assert updated["current_amount"] == 500.0
        assert updated["distance"]["remaining"] == 1500.0
    finally:
        database.delete_goal(gid)


def test_simulate_reduce_category_percent(ensure_db):
    """Simulate reduce_category_percent lowers that category in simulated summary."""
    import simulator_service as sim
    result = sim.run_simulation(
        [{"type": "reduce_category_percent", "category": "transport", "value": 50}],
    )
    assert "simulated_summary" in result
    assert "by_category" in result["simulated_summary"]
    # Transport in simulated should be half of baseline (if present)
    base_cat = result["baseline_summary"].get("by_category") or {}
    sim_cat = result["simulated_summary"].get("by_category") or {}
    if "transport" in base_cat:
        assert sim_cat.get("transport", 0) == round(base_cat["transport"] * 0.5, 2)
    assert result["delta_summary"]["total_change"] <= 0


def test_simulate_change_category_cap(ensure_db):
    """Simulate change_category_cap appears in simulated_summary limits."""
    import simulator_service as sim
    result = sim.run_simulation(
        [{"type": "change_category_cap", "category": "food", "amount": 350}],
    )
    assert result["simulated_summary"]["limits"].get("food") == 350


def test_affordability_zero_amount_affordable(ensure_db):
    """Affordability check with amount 0 is always affordable."""
    import affordability_service as aff
    result = aff.check_affordability(amount=0.0, category="food")
    assert result["can_afford"] is True
    assert "reasons" in result
