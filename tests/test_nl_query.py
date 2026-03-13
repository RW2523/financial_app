"""
Tests for safe NL query: category total, merchant filter, top month, ambiguous fallback, out-of-scope refusal.
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
import database
from nl_query_service import (
    answer_question,
    is_out_of_scope,
    parse_question_rules,
    validate_and_resolve,
    execute_query,
    format_answer,
)


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


# ----- Out-of-scope refusal -----

def test_refusal_for_out_of_scope_question():
    """Questions asking for financial advice should be refused."""
    r = answer_question("Should I invest in stocks?")
    assert r.get("refused") is True
    assert "only" in r.get("answer_text", "").lower() or "can't" in r.get("answer_text", "").lower()


def test_refusal_for_prediction():
    """Questions asking for prediction should be refused."""
    r = answer_question("What will my expenses be next year?")
    assert r.get("refused") is True


# ----- Category total -----

def test_category_total_question(ensure_db):
    """Question about category spend returns sum and rows."""
    r = answer_question("How much did I spend on food last month?")
    assert r.get("refused") is False
    assert "parsed_query" in r
    assert r["parsed_query"].get("category") == "food" or r["parsed_query"].get("intent") in ("sum", "category_total")
    assert "answer_text" in r
    assert "rows" in r
    assert isinstance(r["rows"], list)


# ----- Merchant filter -----

def test_merchant_filter_question(ensure_db):
    """Question about Uber expenses above 20 parses merchant and min_amount."""
    r = answer_question("Show Uber expenses above 20 dollars")
    assert r.get("refused") is False
    pq = r.get("parsed_query") or {}
    assert pq.get("merchant") == "uber" or "uber" in (pq.get("merchant") or "")
    assert pq.get("min_amount") == 20 or (pq.get("min_amount") is not None and pq.get("min_amount") >= 20)


# ----- Top month -----

def test_top_month_question(ensure_db):
    """Which month had highest grocery spend -> intent top_month."""
    r = answer_question("Which month had the highest grocery spend?")
    assert r.get("refused") is False
    assert r["parsed_query"].get("intent") == "top_month"
    assert "answer_text" in r


# ----- Safe fallback on ambiguous -----

def test_safe_fallback_ambiguous_question(ensure_db):
    """Ambiguous or unparseable question still returns safe response (no crash, no raw SQL)."""
    r = answer_question("xyz random gibberish 123")
    assert "parsed_query" in r
    assert "answer_text" in r
    assert "rows" in r
    assert r.get("refused") is False
    # Should not contain any SQL
    raw = str(r)
    assert "SELECT" not in raw and "DELETE" not in raw and "INSERT" not in raw
