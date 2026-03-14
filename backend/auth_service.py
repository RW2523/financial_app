"""
Simple auth: username + password, user profile (salary, monthly_budget).
Passwords hashed with SHA-256 + salt. No JWT; frontend sends X-User-Id after login.
"""
import hashlib
import secrets
from typing import Optional, Dict, Any

import database

SALT = "expense_tracker_auth_v1"  # Change in production or use env


def _hash_password(password: str) -> str:
    return hashlib.sha256((SALT + password).encode()).hexdigest()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Return user row by username or None."""
    return database.get_user_by_username(username)


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Return user row by id or None."""
    return database.get_user_by_id(user_id)


def verify_password(user: Dict[str, Any], password: str) -> bool:
    pw_hash = (user.get("password_hash") or "").strip()
    return bool(pw_hash and _hash_password(password) == pw_hash)


def register(username: str, password: str, salary: float = 0, monthly_budget: float = 0, currency: str = "USD") -> Dict[str, Any]:
    """Create new user. Raises ValueError if username exists."""
    username_clean = (username or "").strip().lower()
    if not username_clean or len(username_clean) < 2:
        raise ValueError("Username must be at least 2 characters.")
    if not password or len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")
    if get_user_by_username(username_clean):
        raise ValueError("Username already taken.")
    user_id = f"user_{secrets.token_hex(8)}"
    password_hash = _hash_password(password)
    database.create_user(
        user_id=user_id,
        username=username_clean,
        password_hash=password_hash,
        salary=salary,
        monthly_budget=monthly_budget,
        currency=currency,
    )
    return database.get_user_by_id(user_id) or {}


def login(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify credentials and return user dict (without password_hash) or None."""
    user = get_user_by_username((username or "").strip().lower())
    if not user or not verify_password(user, password):
        return None
    out = dict(user)
    out.pop("password_hash", None)
    return out
