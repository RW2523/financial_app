"""
Unit tests for request-scoped user context (multi-user readiness).
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
from context import get_current_user_id, set_current_user_id
from config import DEFAULT_USER_ID


def test_get_current_user_id_returns_default_when_unset():
    """Without set_current_user_id, get_current_user_id returns DEFAULT_USER_ID."""
    set_current_user_id(None)
    assert get_current_user_id() == DEFAULT_USER_ID


def test_set_current_user_id_overrides():
    """set_current_user_id overrides the returned value."""
    set_current_user_id("user_123")
    try:
        assert get_current_user_id() == "user_123"
    finally:
        set_current_user_id(None)


def test_set_current_user_id_none_resets_to_default():
    """set_current_user_id(None) resets to default."""
    set_current_user_id("other")
    set_current_user_id(None)
    assert get_current_user_id() == DEFAULT_USER_ID
