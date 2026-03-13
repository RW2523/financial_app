"""
Tests for advanced insights: delta calculation, weekday vs weekend, anomaly detection, trend consistency.
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

from insights_service import (
    compute_overview,
    compute_trends,
    compute_categories,
    compute_anomalies,
    _filter_by_range,
    _prev_period,
    _total_spend,
)


# ----- Delta calculation -----

def test_delta_calculation():
    """Spend delta vs previous period is current total - previous total."""
    current = [
        {"date": "2025-02-10", "amount": 100, "category": "food"},
        {"date": "2025-02-11", "amount": 50, "category": "transport"},
    ]
    previous = [
        {"date": "2025-01-10", "amount": 80, "category": "food"},
        {"date": "2025-01-11", "amount": 20, "category": "transport"},
    ]
    ov = compute_overview(
        current, "2025-02-01", "2025-02-28",
        previous_period_expenses=previous,
    )
    assert ov["total_spend"] == 150
    assert ov["spend_delta"] == 50  # 150 - 100
    assert ov["spend_delta_percent"] == 50.0  # 50% increase


def test_delta_no_previous():
    """When previous period not provided, delta fields are None."""
    expenses = [{"date": "2025-02-10", "amount": 100, "category": "food"}]
    ov = compute_overview(expenses, "2025-02-01", "2025-02-28")
    assert ov["spend_delta"] is None
    assert ov["spend_delta_percent"] is None


# ----- Weekday vs weekend -----

def test_weekday_vs_weekend_analysis():
    """Weekday total and weekend total are computed from day of week."""
    # 2025-02-01 is Saturday, 2025-02-02 Sunday, 2025-02-03 Monday
    expenses = [
        {"date": "2025-02-01", "amount": 50, "category": "other"},   # Saturday
        {"date": "2025-02-02", "amount": 30, "category": "other"},   # Sunday
        {"date": "2025-02-03", "amount": 20, "category": "other"},   # Monday
    ]
    ov = compute_overview(expenses, "2025-02-01", "2025-02-28")
    ww = ov["weekday_vs_weekend"]
    assert ww["weekend_total"] == 80  # 50 + 30
    assert ww["weekday_total"] == 20


# ----- Anomaly detection -----

def test_anomaly_z_score_within_category():
    """High amount within a category is flagged when z-score exceeds threshold."""
    expenses = [
        {"id": 1, "date": "2025-02-01", "amount": 10, "category": "food", "merchant": "A"},
        {"id": 2, "date": "2025-02-02", "amount": 12, "category": "food", "merchant": "B"},
        {"id": 3, "date": "2025-02-03", "amount": 11, "category": "food", "merchant": "C"},
        {"id": 4, "date": "2025-02-04", "amount": 100, "category": "food", "merchant": "D"},  # outlier
    ]
    result = compute_anomalies(expenses, "2025-02-01", "2025-02-28", z_threshold=2.0)
    assert len(result["anomalies"]) >= 1
    reasons = [a["reason"] for a in result["anomalies"]]
    assert "high_z_score_within_category" in reasons or "top_percentile" in reasons


def test_anomaly_empty_period():
    """Empty period returns empty anomalies."""
    result = compute_anomalies([], "2025-02-01", "2025-02-28")
    assert result["anomalies"] == []


# ----- Trend output consistency -----

def test_trend_output_consistency():
    """Trends return consistent structure: months, trends list with label, total_spend, by_category."""
    expenses = [
        {"date": "2025-01-15", "amount": 50, "category": "food"},
        {"date": "2025-02-15", "amount": 60, "category": "food"},
    ]
    result = compute_trends(expenses, months=2)
    assert "months" in result
    assert "trends" in result
    assert result["months"] == 2
    assert len(result["trends"]) == 2
    for t in result["trends"]:
        assert "label" in t
        assert "total_spend" in t
        assert "transaction_count" in t
        assert "by_category" in t


def test_categories_breakdown():
    """Categories endpoint returns total and breakdown with percent."""
    expenses = [
        {"date": "2025-02-01", "amount": 60, "category": "food"},
        {"date": "2025-02-02", "amount": 40, "category": "transport"},
    ]
    result = compute_categories(expenses, "2025-02-01", "2025-02-28")
    assert result["total"] == 100
    assert len(result["breakdown"]) == 2
    percents = [b["percent"] for b in result["breakdown"]]
    assert sum(percents) == 100.0
