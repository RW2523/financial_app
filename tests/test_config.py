"""
Unit tests for centralized config: thresholds, paths, is_auto_verified.
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
from config import (
    is_auto_verified,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    DEFAULT_USER_ID,
    NEAR_LIMIT_PERCENT,
    DATABASE_PATH,
    SQLITE_TIMEOUT,
)


def test_is_auto_verified_high():
    assert is_auto_verified(CONFIDENCE_HIGH) is True
    assert is_auto_verified(0.9) is True


def test_is_auto_verified_below_high():
    assert is_auto_verified(CONFIDENCE_MEDIUM) is False
    assert is_auto_verified(0.5) is False
    assert is_auto_verified(0.0) is False


def test_is_auto_verified_none():
    assert is_auto_verified(None) is False


def test_default_user_id_non_empty_string():
    assert isinstance(DEFAULT_USER_ID, str)
    assert len(DEFAULT_USER_ID) > 0


def test_near_limit_percent_in_range():
    assert 1 <= NEAR_LIMIT_PERCENT <= 100


def test_database_path_under_project():
    assert "database" in DATABASE_PATH
    assert DATABASE_PATH.endswith(".db") or "expenses" in DATABASE_PATH


def test_sqlite_timeout_positive():
    assert SQLITE_TIMEOUT > 0
