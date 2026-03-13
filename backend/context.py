"""
Request-scoped user context for multi-user readiness.
Single-user mode: get_current_user_id() always returns DEFAULT_USER_ID.
Later: set from auth middleware (e.g. JWT or API key) per request.
"""
from typing import Optional

try:
    from config import DEFAULT_USER_ID
except ImportError:
    DEFAULT_USER_ID = "local"

# Thread-local or process-global for current request (no async context in FastAPI by default; use same for all in single-user)
_current_user_id: Optional[str] = None


def get_current_user_id() -> str:
    """Return current user id for this request. Defaults to DEFAULT_USER_ID in single-user mode."""
    global _current_user_id
    if _current_user_id is not None:
        return _current_user_id
    return DEFAULT_USER_ID


def set_current_user_id(user_id: Optional[str]) -> None:
    """Set current user id (e.g. from auth middleware). None resets to default."""
    global _current_user_id
    _current_user_id = user_id
