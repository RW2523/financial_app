"""
Tests for hybrid expense extraction: deterministic parsing, merchant extraction,
confidence scoring, and fallback behavior.
"""
import sys
import os

# Run from project root so backend is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest
from datetime import datetime

from extraction_service import (
    extract_amount_currency,
    parse_relative_date,
    extract_merchant,
    normalize_merchant,
    infer_category_from_rules,
    compute_confidence,
    extract_expense,
)


# ----- Amount & currency -----

@pytest.mark.parametrize("text,expected_amount,expected_currency", [
    ("$50", 50.0, "USD"),
    ("50 dollars", 50.0, "USD"),
    ("18 bucks", 18.0, "USD"),
    ("INR 500", 500.0, "INR"),
    ("€12", 12.0, "EUR"),
    ("paid 25.99 USD", 25.99, "USD"),
    ("like 30 dollars", 30.0, "USD"),
    ("about 10 euros", 10.0, "EUR"),
])
def test_deterministic_amount_currency(text, expected_amount, expected_currency):
    amount, currency, from_rules = extract_amount_currency(text)
    assert amount == expected_amount
    assert currency == expected_currency
    assert from_rules is True


def test_amount_currency_no_match():
    amount, currency, from_rules = extract_amount_currency("nothing here")
    assert amount is None
    assert from_rules is False


# ----- Relative date -----

def test_relative_date_today():
    today = datetime(2026, 2, 6)
    out = parse_relative_date("spent today on coffee", today)
    assert out == "2026-02-06"


def test_relative_date_yesterday():
    today = datetime(2026, 2, 6)
    out = parse_relative_date("yesterday I bought food", today)
    assert out == "2026-02-05"


def test_relative_date_last_night():
    today = datetime(2026, 2, 6)
    out = parse_relative_date("last night at the bar", today)
    assert out == "2026-02-05"


def test_relative_date_no_match():
    today = datetime(2026, 2, 6)
    out = parse_relative_date("random text", today)
    assert out is None


# ----- Merchant -----

@pytest.mark.parametrize("text,expected_merchant", [
    ("at Starbucks for coffee", "starbucks"),
    ("from Uber to airport", "uber"),
    ("paid Amazon for order", "amazon"),
    ("to Walmart for groceries", "walmart"),
])
def test_merchant_extraction(text, expected_merchant):
    merchant, from_rules = extract_merchant(text)
    assert from_rules is True
    assert expected_merchant in (merchant or "")


def test_merchant_normalization():
    assert normalize_merchant("  Starbucks  ") == "starbucks"
    assert normalize_merchant("Uber Eats") == "ubereats"


# ----- Category inference -----

def test_category_from_merchant():
    assert infer_category_from_rules("at Starbucks", "starbucks") == "food"
    assert infer_category_from_rules("from Uber", "uber") == "transport"
    assert infer_category_from_rules("paid Amazon", "amazon") == "shopping"


def test_category_from_keywords():
    assert infer_category_from_rules("groceries at the store", None) == "food"
    assert infer_category_from_rules("uber to work", None) == "transport"
    assert infer_category_from_rules("netflix subscription", None) == "entertainment"


def test_category_no_match():
    assert infer_category_from_rules("something random", None) is None


# ----- Confidence -----

def test_confidence_high_when_all_from_rules():
    score = compute_confidence(
        amount_from_rules=True,
        currency_from_rules=True,
        date_from_rules=True,
        category_from_rules=True,
        merchant_from_rules=True,
        has_amount=True,
        has_date=True,
    )
    assert score >= 0.9


def test_confidence_lower_when_llm_used():
    score = compute_confidence(
        amount_from_rules=False,
        currency_from_rules=False,
        date_from_rules=False,
        category_from_rules=False,
        merchant_from_rules=False,
        has_amount=True,
        has_date=True,
    )
    assert score < 0.5


# ----- Full extraction (rule-only path when amount + date + category from rules) -----

def test_extract_expense_rule_only():
    """When text has amount, relative date, and category cues, LLM may not be called (mocked in unit test we only assert structure)."""
    text = "50 dollars on groceries yesterday at Trader Joe"
    result = extract_expense(text, source_type="web_text")
    assert result.amount == 50.0
    assert result.currency == "USD"
    assert result.date  # YYYY-MM-DD
    assert result.category in ("food", "other") or "food" in (result.category or "")
    assert result.confidence_score >= 0
    assert result.confidence_score <= 1.0
    assert result.evidence is not None
    assert result.raw_text == text


def test_extract_expense_has_verification_metadata():
    text = "$20 at Starbucks this morning"
    result = extract_expense(text, source_type="telegram_text")
    assert result.extracted_json is not None
    assert "confidence_score" in result.extracted_json
    assert "date" in result.extracted_json
    assert "category" in result.extracted_json
