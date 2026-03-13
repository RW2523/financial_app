"""
Tests for merchant memory: normalization, lookup from DB, persistence, fallback when unknown.
Uses real database (database/expenses.db); init_database ensures tables exist.
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
from merchant_service import normalize_merchant, lookup_merchant_mapping, remember_merchant_mapping
from extraction_service import extract_expense, lookup_category_from_merchant_memory


@pytest.fixture(scope="module")
def ensure_db():
    database.init_database()


# ----- Normalization -----

def test_merchant_normalization():
    assert normalize_merchant("  Starbucks  ") == "starbucks"
    assert normalize_merchant("Uber Eats") == "ubereats"
    assert normalize_merchant("") == ""
    assert normalize_merchant("WALMART") == "walmart"


# ----- Lookup from memory (requires DB) -----

def test_lookup_merchant_mapping_unknown(ensure_db):
    assert lookup_merchant_mapping("nonexistent_merchant_xyz_123") is None


def test_persistence_and_lookup_merchant_mapping(ensure_db):
    """Remember a mapping then lookup; category and subcategory persist."""
    name = "test_persist_merchant_abc"
    remember_merchant_mapping(name, "shopping", subcategory="groceries", confidence_score=0.9)
    out = lookup_merchant_mapping(name)
    assert out is not None
    assert out[0] == "shopping"
    assert out[1] == "groceries"


def test_category_lookup_from_merchant_memory(ensure_db):
    """lookup_category_from_merchant_memory returns (category, subcategory) when merchant is in DB."""
    name = "test_lookup_merchant_def"
    database.upsert_merchant(name, "food", display_name=name, subcategory="coffee")
    mem = lookup_category_from_merchant_memory(name)
    assert mem is not None
    assert mem[0] == "food"
    assert mem[1] == "coffee"


def test_fallback_when_merchant_unknown():
    """When merchant is not in memory, extract_expense falls back to rules (or LLM). Result still has category."""
    text = "18 dollars at SomeUnknownPlaceNobodyStored"
    result = extract_expense(text)
    assert result.amount == 18.0
    assert result.currency == "USD"
    assert result.category in ("other", "shopping", "food", "entertainment", "transport", "utilities", "healthcare")


def test_extract_uses_merchant_memory_when_known(ensure_db):
    """When merchant is in DB, extraction should prefer stored category."""
    name = "test_extract_prefer_memory"
    database.upsert_merchant(name, "entertainment", display_name=name, subcategory="streaming")
    text = f"42 dollars at {name}"
    result = extract_expense(text)
    assert result.merchant == name
    assert result.category == "entertainment"
    assert result.subcategory == "streaming"
    assert result.amount == 42.0
