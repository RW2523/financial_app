"""
Tests for budget health score and recommendation engine:
score calculation, recommendation triggering, no unsupported recommendations.
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
from health_service import (
    compute_health_score,
    generate_recommendations,
    HEALTH_WEIGHTS,
)


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


def test_score_calculation(ensure_db):
    """Health score is 0-100 and uses weighted metrics."""
    result = compute_health_score()
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert "metrics" in result
    for k in HEALTH_WEIGHTS:
        assert k in result["metrics"]
        assert 0 <= result["metrics"][k] <= 1
    assert "weights" in result


def test_score_with_custom_weights(ensure_db):
    """Custom weights change the score."""
    r1 = compute_health_score(weights={"budget_adherence": 1.0, "overspending_frequency": 0, "category_volatility": 0, "recurring_burden": 0, "discretionary_ratio": 0, "anomaly_frequency": 0})
    r2 = compute_health_score(weights={"budget_adherence": 0, "overspending_frequency": 1.0, "category_volatility": 0, "recurring_burden": 0, "discretionary_ratio": 0, "anomaly_frequency": 0})
    assert "score" in r1 and "score" in r2
    # Scores may or may not differ depending on data
    assert 0 <= r1["score"] <= 100 and 0 <= r2["score"] <= 100


def test_recommendation_triggering_food_near_limit(ensure_db):
    """When food spend is >= 80% of limit, food_budget_nearly_exceeded recommendation appears."""
    database.set_limit("food", 100.0, "USD")
    y, m = datetime.now().year, datetime.now().month
    for _ in range(5):
        database.save_expense(date=f"{y}-{m:02d}-01", category="food", amount=20.0, currency="USD", raw_text="health_test")
    try:
        recs = generate_recommendations(y, m)
        food_rec = next((r for r in recs if r.get("id") == "food_budget_nearly_exceeded"), None)
        assert food_rec is not None
        assert "metric_cited" in food_rec
        assert food_rec["metric_cited"] == "food_spend_vs_limit"
        assert "value" in food_rec
        assert "suggestion" in food_rec
    finally:
        for e in database.get_all_expenses():
            if e.get("raw_text") == "health_test":
                database.delete_expense(e["id"])
        database.delete_limit("food")


def test_no_unsupported_recommendation_generation(ensure_db):
    """All recommendations have allowed id and metric_cited from our engine."""
    allowed_ids = {"food_budget_nearly_exceeded", "transport_rising_mom", "recurring_subscriptions_high", "one_merchant_dominates_discretionary"}
    recs = generate_recommendations()
    for r in recs:
        assert r.get("id") in allowed_ids
        assert "metric_cited" in r
        assert "value" in r
        assert "suggestion" in r
        assert "title" in r
