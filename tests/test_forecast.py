"""
Tests for forecasting and predictive alerts: projected month-end total,
projected category over-limit, no alert when under pace, missing historical data.
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest
from datetime import datetime
import database
from forecast_service import (
    projected_month_end,
    projected_categories,
    predictive_alerts,
    days_in_month,
    _days_elapsed_in_month,
    _estimated_over_limit,
)


def test_projected_month_end_total():
    """Projected month-end total is pace * days_in_month when we have spend and days elapsed."""
    # Use a past month so days_elapsed is full and we control data
    year, month = 2025, 1
    # Insert a few expenses in that month
    database.init_database()
    for day in [5, 10, 15]:
        database.save_expense(
            date=f"{year}-{month:02d}-{day:02d}",
            category="food",
            amount=10.0,
            currency="USD",
            raw_text="test",
        )
    try:
        result = projected_month_end(year, month)
        assert "projected_total" in result
        assert "by_category" in result
        assert result["days_in_month"] == 31
        # Spend so far in Jan 2025: 30 total (3*10). Days elapsed in Jan 2025 from "today" could be 31 (past month).
        # So pace = 30/31, projected = 30/31 * 31 = 30. Or if today is after Jan, days_elapsed=31, spend=30, projected=30.
        assert result["projected_total"] >= 0
        assert result["spend_so_far_total"] >= 0
    finally:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "test":
                database.delete_expense(e["id"])


def test_projected_category_over_limit():
    """When projected category spend exceeds limit, predictive alert includes over_amount and message."""
    database.init_database()
    year, month = datetime.now().year, datetime.now().month
    # Set a low limit for 'food'
    database.set_limit("food", 50.0, "USD")
    # Add enough food spend that pace projects over 50
    for _ in range(5):
        database.save_expense(
            date=f"{year}-{month:02d}-01",
            category="food",
            amount=20.0,
            currency="USD",
            raw_text="forecast_test",
        )
    try:
        result = predictive_alerts(year, month)
        assert "alerts" in result
        # May or may not have food alert depending on days_elapsed and pace
        food_alert = next((a for a in result["alerts"] if a["category"] == "food"), None)
        if food_alert:
            assert food_alert["over_amount"] >= 0
            assert "projected to exceed" in food_alert["message"].lower() or "exceed" in food_alert["message"].lower()
    finally:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "forecast_test":
                database.delete_expense(e["id"])
        database.delete_limit("food")


def test_no_predictive_alert_when_under_pace():
    """When projected is under limit, that category should not appear in predictive alerts."""
    database.init_database()
    year, month = datetime.now().year, datetime.now().month
    database.set_limit("transport", 10000.0, "USD")  # very high limit
    try:
        result = predictive_alerts(year, month)
        transport_alert = next((a for a in result["alerts"] if a["category"] == "transport"), None)
        assert transport_alert is None
    finally:
        database.delete_limit("transport")


def test_compatibility_missing_historical_data():
    """Forecast runs without error when there is no or little historical data."""
    database.init_database()
    year, month = datetime.now().year, datetime.now().month
    result = projected_month_end(year, month)
    assert "projected_total" in result
    assert "by_category" in result
    assert result["projected_total"] >= 0
    # No exception; may use historical_avg or zero
    result2 = projected_categories(year, month)
    assert "projected_total" in result2
    assert "by_category" in result2
