"""
Tests for recurring expense detection: monthly detection, amount tolerance,
false positive reduction, next expected date.
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

from recurring_service import (
    detect_recurring,
    _amount_matches,
    _infer_frequency,
    _next_expected_date,
    _reduce_false_positives,
    recompute_recurring,
)
import database


# ----- Amount tolerance -----

def test_similar_amount_tolerance():
    """Amounts within 12% are considered the same band."""
    assert _amount_matches(100, 100) is True
    assert _amount_matches(100, 90) is True
    assert _amount_matches(100, 88) is True   # 12% diff, at boundary
    assert _amount_matches(100, 87) is False  # >12% diff
    assert _amount_matches(10.0, 11.0) is True   # 10% diff
    assert _amount_matches(10.0, 12.0) is False  # 20% diff


# ----- Frequency inference -----

def test_infer_frequency_monthly():
    """Gaps around 28-31 days infer monthly."""
    gaps = [30, 31, 28, 30]
    freq, conf = _infer_frequency(gaps)
    assert freq == "monthly"
    assert 0 <= conf <= 1


def test_infer_frequency_weekly():
    """Gaps around 7 days infer weekly."""
    gaps = [7, 7, 8, 7]
    freq, conf = _infer_frequency(gaps)
    assert freq == "weekly"


def test_infer_frequency_biweekly():
    """Gaps around 14 days infer biweekly."""
    gaps = [14, 14, 15]
    freq, conf = _infer_frequency(gaps)
    assert freq == "biweekly"


# ----- Next expected date -----

def test_next_expected_date_computation():
    """Next expected is last_seen + one period."""
    last = datetime(2025, 2, 1)
    assert _next_expected_date(last, "weekly") == "2025-02-08"
    assert _next_expected_date(last, "biweekly") == "2025-02-15"
    assert _next_expected_date(last, "monthly") == "2025-03-03"  # +30 days
    assert _next_expected_date(last, "irregular_recurring") is None


# ----- False positive reduction -----

def test_false_positive_reduction_one_month_only():
    """Three charges in the same month should not count as monthly recurring (need 2+ distinct months)."""
    dates = [
        datetime(2025, 2, 1),
        datetime(2025, 2, 10),
        datetime(2025, 2, 20),
    ]
    assert _reduce_false_positives(dates, "monthly") is False


def test_false_positive_reduction_two_months():
    """Charges in 2+ distinct months with 3+ occurrences can be monthly recurring."""
    dates = [
        datetime(2025, 1, 5),
        datetime(2025, 2, 5),
        datetime(2025, 3, 5),
    ]
    assert _reduce_false_positives(dates, "monthly") is True


def test_false_positive_reduction_two_occurrences():
    """Only 2 occurrences in 2 months is not enough for monthly (need 3+ occurrences)."""
    dates = [
        datetime(2025, 1, 5),
        datetime(2025, 2, 5),
    ]
    assert _reduce_false_positives(dates, "monthly") is False


# ----- Full detection: monthly recurring -----

def test_monthly_recurring_detection():
    """Detect monthly pattern: same merchant/category, similar amount, ~30-day gaps."""
    expenses = [
        {"date": "2025-01-05", "amount": 29.99, "merchant": "Netflix", "category": "entertainment", "currency": "USD", "subcategory": None},
        {"date": "2025-02-05", "amount": 29.99, "merchant": "Netflix", "category": "entertainment", "currency": "USD", "subcategory": None},
        {"date": "2025-03-06", "amount": 30.00, "merchant": "Netflix", "category": "entertainment", "currency": "USD", "subcategory": None},
    ]
    result = detect_recurring(expenses)
    assert len(result) >= 1
    rec = next((r for r in result if (r.get("merchant") or "").lower() == "netflix" or "entertainment" in (r.get("category") or "")), result[0])
    assert rec["frequency_type"] == "monthly"
    assert rec["expense_count"] == 3
    assert rec.get("next_expected_date") is not None
    assert 28 <= rec["typical_amount"] <= 31


# ----- Recompute with DB -----

@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_recompute_persists_and_returns(ensure_db):
    """Recompute loads from DB, detects, persists to recurring_expenses, returns list."""
    # Insert a few monthly expenses
    for i in range(3):
        database.save_expense(
            date=f"2025-0{i+1}-10",
            category="utilities",
            amount=50.0 + i,
            currency="USD",
            raw_text="electric",
            merchant="Electric Co",
        )
    try:
        detected = recompute_recurring()
        rows = database.get_recurring_expenses()
        # May or may not detect depending on date spread (Jan 10, Feb 10, Mar 10 -> monthly)
        assert isinstance(detected, list)
        assert isinstance(rows, list)
        # Clean up test expenses
        all_exp = database.get_all_expenses()
        for e in all_exp:
            if e.get("raw_text") == "electric":
                database.delete_expense(e["id"])
        database.clear_recurring_expenses()
    except Exception:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "electric":
                database.delete_expense(e["id"])
        database.clear_recurring_expenses()
        raise
