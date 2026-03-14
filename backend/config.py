"""
Centralized configuration: paths, thresholds, feature flags, env.
Single-user local-first: DEFAULT_USER_ID is used when no user context is provided.
"""
import os
from typing import Optional

# ----- Paths -----
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(_BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "expenses.db")

# ----- User (multi-user readiness) -----
# When no user is authenticated, all data is scoped to this id. Existing data is migrated to it.
DEFAULT_USER_ID = os.environ.get("EXPENSE_DEFAULT_USER_ID", "local")

# ----- DB -----
SQLITE_TIMEOUT = 20  # seconds to wait for lock

# ----- Confidence & verification -----
CONFIDENCE_HIGH = 0.85   # auto-verified
CONFIDENCE_MEDIUM = 0.6  # saved but flagged; below = needs review

def is_auto_verified(confidence_score: Optional[float]) -> bool:
    """True if expense is auto-verified (high confidence)."""
    if confidence_score is None:
        return False
    return confidence_score >= CONFIDENCE_HIGH

# ----- Limits & alerts -----
NEAR_LIMIT_PERCENT = 80  # Alert when spending >= 80% of limit

# ----- Feature flags (env) -----
def feature_gmail_sync() -> bool:
    return os.environ.get("EXPENSE_GMAIL_ENABLED", "1").strip().lower() in ("1", "true", "yes")

def feature_telegram() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())

# ----- LLM / model (for future tuning) -----
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# ----- API -----
EXPENSE_API_URL = os.environ.get("EXPENSE_API_URL", "http://127.0.0.1:8000")

# ----- Tavily (finance news) -----
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
