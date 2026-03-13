"""
Tests for low-confidence correction workflow: confidence classification,
review queue filtering, verify endpoint, correction persistence, delete.
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
import json as _json

import database
from config import is_auto_verified, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


# ----- A. Confidence threshold logic -----

def test_confidence_classification_high():
    assert is_auto_verified(0.9) is True
    assert is_auto_verified(CONFIDENCE_HIGH) is True


def test_confidence_classification_medium_and_low():
    assert is_auto_verified(0.7) is False  # below high
    assert is_auto_verified(CONFIDENCE_MEDIUM) is False
    assert is_auto_verified(0.5) is False
    assert is_auto_verified(0.0) is False
    assert is_auto_verified(None) is False


# ----- B. Review queue filtering -----

def test_review_queue_filtering(ensure_db):
    """Expenses with is_verified=0 or low confidence appear in review queue."""
    high_id = database.save_expense(
        date="2025-02-01",
        category="food",
        amount=10.0,
        currency="USD",
        raw_text="coffee",
        is_verified=1,
        confidence_score=0.9,
    )
    low_id = database.save_expense(
        date="2025-02-02",
        category="other",
        amount=5.0,
        currency="USD",
        raw_text="misc",
        is_verified=0,
        confidence_score=0.5,
    )
    try:
        data = database.get_expenses_for_review(confidence_threshold=CONFIDENCE_MEDIUM)
        ids = [x["id"] for x in data]
        assert low_id in ids
        assert high_id not in ids
    finally:
        database.delete_expense(high_id)
        database.delete_expense(low_id)


# ----- Verify logic (update_expense + is_verified) -----

def test_verify_updates_expense_and_verified(ensure_db):
    """Simulate verify: update expense with corrected fields and set is_verified=1."""
    eid = database.save_expense(
        date="2025-02-03",
        category="other",
        amount=20.0,
        currency="USD",
        raw_text="something",
        is_verified=0,
        confidence_score=0.5,
    )
    try:
        database.update_expense(
            eid,
            is_verified=1,
            category="transport",
            amount=25.0,
            correction_json=_json.dumps({"category": "transport", "amount": 25.0}),
        )
        row = database.get_expense(eid)
        assert row["is_verified"] == 1
        assert row["category"] == "transport"
        assert row["amount"] == 25.0
        assert row["date"] == "2025-02-03"
    finally:
        database.delete_expense(eid)


# ----- Correction persistence -----

def test_correction_persistence(ensure_db):
    """When we update with correction_json, it is stored and expense fields are updated."""
    eid = database.save_expense(
        date="2025-02-04",
        category="food",
        amount=15.0,
        currency="USD",
        raw_text="lunch",
        is_verified=0,
        extracted_json='{"date":"2025-02-04","category":"food"}',
        correction_json=None,
    )
    try:
        correction = {"date": "2025-02-05", "category": "entertainment", "amount": 15.0, "currency": "USD"}
        database.update_expense(
            eid,
            is_verified=1,
            date="2025-02-05",
            category="entertainment",
            correction_json=_json.dumps(correction),
        )
        row = database.get_expense(eid)
        assert row["correction_json"] is not None
        corr = _json.loads(row["correction_json"])
        assert corr.get("date") == "2025-02-05"
        assert corr.get("category") == "entertainment"
        assert row["date"] == "2025-02-05"
        assert row["category"] == "entertainment"
    finally:
        database.delete_expense(eid)


# ----- Delete (reject) -----

def test_delete_expense(ensure_db):
    """delete_expense removes the expense and returns True; second call returns False."""
    eid = database.save_expense(
        date="2025-02-06",
        category="other",
        amount=1.0,
        currency="USD",
        raw_text="to delete",
    )
    ok = database.delete_expense(eid)
    assert ok is True
    assert database.get_expense(eid) is None
    ok2 = database.delete_expense(eid)
    assert ok2 is False
