import sqlite3
from datetime import datetime
from typing import List, Dict
import os

# Database at project root: expense-tracker/database/expenses.db
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(_BASE_DIR, "database", "expenses.db")


def init_database():
    """Initialize SQLite database and create expenses table"""
    db_dir = os.path.dirname(DATABASE_PATH)
    os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()


def save_expense(date: str, category: str, amount: float, currency: str, raw_text: str) -> int:
    """Save expense to database"""
    conn = sqlite3.connect(DATABASE_PATH)
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
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_monthly_expenses(year: int, month: int) -> List[Dict]:
    """Get all expenses for a specific month"""
    conn = sqlite3.connect(DATABASE_PATH)
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
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
