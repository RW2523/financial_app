import sqlite3
from datetime import datetime
from typing import List, Dict
import os

# Database at project root: expense-tracker/database/expenses.db
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(_BASE_DIR, "database", "expenses.db")

# Avoid "database is locked" when web + Telegram hit DB at once
SQLITE_TIMEOUT = 20  # seconds to wait for lock


def init_database():
    """Initialize SQLite database and create expenses table"""
    db_dir = os.path.dirname(DATABASE_PATH)
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            raw_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_limits (
            category TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gmail_processed (
            message_id TEXT PRIMARY KEY,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_expense(date: str, category: str, amount: float, currency: str, raw_text: str) -> int:
    """Save expense to database"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expenses (date, category, amount, currency, raw_text)
        VALUES (?, ?, ?, ?, ?)
    """, (date, category, amount, currency, raw_text))

    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return expense_id


def get_expense(expense_id: int) -> Dict:
    """Retrieve single expense by ID"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_monthly_expenses(year: int, month: int) -> List[Dict]:
    """Get all expenses for a specific month"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Match YYYY-MM format at start of date string
    date_pattern = f"{year}-{month:02d}%"

    cursor.execute("""
        SELECT * FROM expenses
        WHERE date LIKE ?
        ORDER BY date DESC
    """, (date_pattern,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_expenses() -> List[Dict]:
    """Get all expenses"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# ---------- Expense limits ----------

def get_limits() -> List[Dict]:
    """Get all expense limits (category -> amount)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT category, amount, currency FROM expense_limits")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_limit(category: str, amount: float, currency: str = "USD") -> None:
    """Set or update limit for a category (use 'total' for overall monthly limit)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expense_limits (category, amount, currency) VALUES (?, ?, ?) "
        "ON CONFLICT(category) DO UPDATE SET amount = ?, currency = ?",
        (category, amount, currency, amount, currency),
    )
    conn.commit()
    conn.close()


def delete_limit(category: str) -> bool:
    """Remove limit for category. Returns True if deleted."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expense_limits WHERE category = ?", (category,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_spending_by_category_for_month(year: int, month: int) -> Dict[str, float]:
    """Return { category: total_amount, 'total': sum } for the given month."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    date_pattern = f"{year}-{month:02d}%"
    cursor.execute(
        "SELECT category, SUM(amount) AS total FROM expenses WHERE date LIKE ? GROUP BY category",
        (date_pattern,),
    )
    rows = cursor.fetchall()
    conn.close()
    by_cat = {row[0]: float(row[1]) for row in rows}
    by_cat["total"] = sum(by_cat.values())
    return by_cat


# ---------- Gmail processed (deduplication) ----------

def gmail_is_processed(message_id: str) -> bool:
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM gmail_processed WHERE message_id = ?", (message_id,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


def gmail_mark_processed(message_id: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO gmail_processed (message_id) VALUES (?)", (message_id,))
    conn.commit()
    conn.close()
