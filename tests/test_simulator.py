"""
Tests for scenario simulator: category reduction, recurring removal, one-time expense, no DB mutation.
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
from simulator_service import run_simulation


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_category_reduction_simulation(ensure_db):
    """Reduce category spend by X% lowers projected total and that category."""
    y, m = datetime.now().year, datetime.now().month
    adjustments = [
        {"type": "reduce_category_percent", "category": "transport", "value": 20},
    ]
    result = run_simulation(adjustments, year=y, month=m)
    baseline = result["baseline_summary"]
    simulated = result["simulated_summary"]
    delta = result["delta_summary"]
    assert "projected_total" in baseline and "projected_total" in simulated
    assert "by_category" in baseline and "by_category" in simulated
    # If there is transport in baseline, simulated transport should be 80% of baseline
    base_trans = baseline["by_category"].get("transport", 0)
    sim_trans = simulated["by_category"].get("transport", 0)
    if base_trans > 0:
        assert sim_trans == round(base_trans * 0.8, 2)
        assert delta["total_change"] <= 0
    assert result["delta_summary"]["total_change"] == round(
        simulated["projected_total"] - baseline["projected_total"], 2
    )


def test_remove_recurring_simulation(ensure_db):
    """Removing a recurring merchant reduces projected total by that subscription's monthly amount."""
    mid = None
    try:
        mid = database.insert_recurring_expense(
            merchant="TestSubSimMerchant",
            category="entertainment",
            subcategory=None,
            typical_amount=15.0,
            currency="USD",
            frequency_type="monthly",
            confidence_score=0.9,
            last_seen_date="2026-01-15",
            next_expected_date="2026-02-15",
            expense_count=3,
            status="active",
        )
        adjustments = [{"type": "remove_recurring_merchant", "merchant": "TestSubSimMerchant"}]
        result = run_simulation(adjustments)
        baseline = result["baseline_summary"]
        simulated = result["simulated_summary"]
        # Simulator subtracts 15 (monthly) from projected total when this recurring is removed
        assert simulated["projected_total"] == round(baseline["projected_total"] - 15.0, 2)
    finally:
        if mid:
            import sqlite3
            conn = sqlite3.connect(database.DATABASE_PATH, timeout=database.SQLITE_TIMEOUT)
            conn.execute("DELETE FROM recurring_expenses WHERE id = ?", (mid,))
            conn.commit()
            conn.close()


def test_one_time_expense_simulation(ensure_db):
    """Adding a one-time expense increases projected total and that category."""
    adjustments = [
        {"type": "add_one_time_expense", "category": "travel", "amount": 300},
    ]
    result = run_simulation(adjustments)
    baseline = result["baseline_summary"]
    simulated = result["simulated_summary"]
    delta = result["delta_summary"]
    assert simulated["projected_total"] == round(baseline["projected_total"] + 300, 2)
    assert simulated["by_category"].get("travel", 0) == round(baseline["by_category"].get("travel", 0) + 300, 2)
    assert delta["total_change"] == 300
    assert delta["by_category"].get("travel") == 300


def test_no_mutation_guarantee(ensure_db):
    """Simulation must not alter database: same expenses and recurring before/after."""
    y, m = datetime.now().year, datetime.now().month
    expenses_before = len(database.get_monthly_expenses(y, m))
    recurring_before = len(database.get_recurring_expenses())
    limits_before = {r["category"]: r["amount"] for r in database.get_limits()}

    run_simulation(
        [
            {"type": "reduce_category_percent", "category": "food", "value": 50},
            {"type": "add_one_time_expense", "category": "other", "amount": 100},
        ],
        year=y,
        month=m,
    )

    expenses_after = len(database.get_monthly_expenses(y, m))
    recurring_after = len(database.get_recurring_expenses())
    limits_after = {r["category"]: r["amount"] for r in database.get_limits()}

    assert expenses_after == expenses_before
    assert recurring_after == recurring_before
    assert limits_after == limits_before


def test_save_fixed_per_week_reduces_total(ensure_db):
    """save_fixed_per_week reduces projected total by ~4.33 * value per month (capped at 0)."""
    adjustments = [{"type": "save_fixed_per_week", "value": 50}]
    result = run_simulation(adjustments)
    baseline = result["baseline_summary"]
    simulated = result["simulated_summary"]
    expected_reduction = round(50 * 4.33, 2)
    expected_total = max(0, round(baseline["projected_total"] - expected_reduction, 2))
    assert simulated["projected_total"] == expected_total
    assert result["delta_summary"]["total_change"] == round(simulated["projected_total"] - baseline["projected_total"], 2)


def test_change_category_cap_in_limits_only(ensure_db):
    """change_category_cap only affects simulated limits in response, not DB."""
    adjustments = [{"type": "change_category_cap", "category": "food", "amount": 999}]
    result = run_simulation(adjustments)
    assert result["simulated_summary"]["limits"].get("food") == 999
    # DB unchanged
    limits = database.get_limits()
    food_limits = [l for l in limits if l["category"] == "food"]
    assert not food_limits or food_limits[0]["amount"] != 999
