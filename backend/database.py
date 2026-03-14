import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Optional
import os

try:
    from config import DATABASE_PATH, SQLITE_TIMEOUT, DEFAULT_USER_ID
except ImportError:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_PATH = os.path.join(_BASE_DIR, "database", "expenses.db")
    SQLITE_TIMEOUT = 20
    DEFAULT_USER_ID = "local"

def _resolve_user_id(user_id: str = None) -> str:
    """Use provided user_id or current context default (avoids circular import of context at module load)."""
    if user_id is not None:
        return user_id
    try:
        from context import get_current_user_id
        return get_current_user_id()
    except ImportError:
        return DEFAULT_USER_ID

# New columns added by schema evolution (backward-compatible)
_EXPENSE_EXTRA_COLUMNS = [
    ("merchant", "TEXT"),
    ("source_type", "TEXT"),
    ("confidence_score", "REAL"),
    ("is_verified", "INTEGER DEFAULT 1"),
    ("extracted_json", "TEXT"),
    ("correction_json", "TEXT"),
    ("subcategory", "TEXT"),
    ("user_id", "TEXT DEFAULT 'local'"),
]


def _ensure_expense_columns(conn):
    """Add new expense columns if missing (safe migration, no data loss)."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expenses)")
    existing = {row[1] for row in cursor.fetchall()}
    for col_name, col_type in _EXPENSE_EXTRA_COLUMNS:
        if col_name not in existing:
            cursor.execute(f"ALTER TABLE expenses ADD COLUMN {col_name} {col_type}")
    conn.commit()


# Use plain types in ALTER TABLE (no UNIQUE); we add a unique index on username separately (SQLite compatibility).
_USER_AUTH_COLUMNS = [
    ("username", "TEXT"),
    ("password_hash", "TEXT"),
    ("salary", "REAL DEFAULT 0"),
    ("monthly_budget", "REAL DEFAULT 0"),
    ("currency", "TEXT DEFAULT 'USD'"),
]


def _ensure_users_and_backfill_user_id(conn):
    """Create users table, ensure default user exists, backfill user_id on expenses. Add auth columns if missing."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            display_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_def in _USER_AUTH_COLUMNS:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
    # Unique index on username so login lookups are unique (avoids UNIQUE in ALTER which can fail on some SQLite).
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)"
    )
    uid = DEFAULT_USER_ID
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, display_name) VALUES (?, ?)",
        (uid, "Local User"),
    )
    # Ensure demo user exists for "Default login"
    _ensure_demo_user(cursor)
    cursor.execute("PRAGMA table_info(expenses)")
    has_user_id = any(row[1] == "user_id" for row in cursor.fetchall())
    if has_user_id:
        cursor.execute("UPDATE expenses SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.commit()


def _ensure_demo_user(cursor):
    """Create demo user if not present (username=demo, password=demo)."""
    import hashlib
    demo_id = "demo"
    cursor.execute("SELECT 1 FROM users WHERE id = ?", (demo_id,))
    if cursor.fetchone():
        return
    pw = hashlib.sha256(("expense_tracker_auth_v1" + "demo").encode()).hexdigest()
    cursor.execute(
        """INSERT INTO users (id, display_name, username, password_hash, salary, monthly_budget, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (demo_id, "Demo User", "demo", pw, 5000.0, 3500.0, "USD"),
    )


def get_user_by_username(username: str) -> Optional[Dict]:
    """Return user row by username (case-insensitive) or None."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username or "",))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Return user row by id or None."""
    if not user_id:
        return None
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_expense_count_for_user(user_id: str) -> int:
    """Return number of expenses for the given user."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expenses)")
    if not any(row[1] == "user_id" for row in cursor.fetchall()):
        conn.close()
        return 0
    cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,))
    n = cursor.fetchone()[0]
    conn.close()
    return n


def create_user(
    user_id: str,
    username: str,
    password_hash: str,
    salary: float = 0,
    monthly_budget: float = 0,
    currency: str = "USD",
) -> None:
    """Insert new user. Raises if username already exists."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO users (id, display_name, username, password_hash, salary, monthly_budget, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, username, username, password_hash, salary, monthly_budget, currency or "USD"),
    )
    conn.commit()
    conn.close()


def _migrate_expense_limits_to_user_scoped(conn):
    """If expense_limits has no user_id, create user-scoped table and migrate."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expense_limits)")
    cols = [row[1] for row in cursor.fetchall()]
    if "user_id" in cols:
        return
    cursor.execute("""
        CREATE TABLE expense_limits_new (
            user_id TEXT NOT NULL DEFAULT 'local',
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            PRIMARY KEY (user_id, category)
        )
    """)
    cursor.execute("SELECT category, amount, currency FROM expense_limits")
    rows = cursor.fetchall()
    uid = DEFAULT_USER_ID
    for row in rows:
        cursor.execute(
            "INSERT INTO expense_limits_new (user_id, category, amount, currency) VALUES (?, ?, ?, ?)",
            (uid, row[0], row[1], row[2] or "USD"),
        )
    cursor.execute("DROP TABLE expense_limits")
    cursor.execute("ALTER TABLE expense_limits_new RENAME TO expense_limits")
    conn.commit()


def init_database():
    """Initialize SQLite database and create expenses table. Applies schema evolution for new columns."""
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
    conn.commit()
    _ensure_expense_columns(conn)
    _ensure_users_and_backfill_user_id(conn)

    # expense_limits: multi-user uses (user_id, category) PK
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_limits (
            category TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD'
        )
    """)
    _migrate_expense_limits_to_user_scoped(conn)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gmail_processed (
            message_id TEXT PRIMARY KEY,
            processed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Merchant memory: learned merchant -> category/subcategory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_name TEXT NOT NULL UNIQUE,
            display_name TEXT,
            default_category TEXT NOT NULL,
            subcategory TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            use_count INTEGER DEFAULT 0
        )
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_merchants_normalized ON merchants(normalized_name)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchant_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL REFERENCES merchants(id),
            alias_text TEXT NOT NULL UNIQUE
        )
    """)

    # Future: per-user overrides (user_id NULL = global/current single-user)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchant_category_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id INTEGER NOT NULL REFERENCES merchants(id),
            user_id TEXT,
            category TEXT NOT NULL,
            subcategory TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(merchant_id, user_id)
        )
    """)

    # Recurring expense insights (detected from historical patterns)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant TEXT,
            category TEXT NOT NULL,
            subcategory TEXT,
            typical_amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            frequency_type TEXT NOT NULL,
            confidence_score REAL,
            last_seen_date TEXT,
            next_expected_date TEXT,
            expense_count INTEGER NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Financial goals (savings_target, spending_reduction, category_cap)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_type TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            target_date TEXT,
            category TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _ensure_column_and_backfill(conn, "financial_goals", "user_id", "TEXT DEFAULT 'local'")

    # Recurring and gmail: add user_id
    _ensure_column_and_backfill(conn, "recurring_expenses", "user_id", "TEXT DEFAULT 'local'")
    _ensure_column_and_backfill(conn, "gmail_processed", "user_id", "TEXT DEFAULT 'local'")
    _ensure_merchants_user_id(conn)

    conn.commit()
    conn.close()


def _ensure_column_and_backfill(conn, table: str, column: str, col_type: str):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    if any(row[1] == column for row in cursor.fetchall()):
        return
    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {column} IS NULL", (DEFAULT_USER_ID,))
    conn.commit()


def _ensure_merchants_user_id(conn):
    """Add user_id to merchants; backfill. Keep existing UNIQUE(normalized_name) for single-user."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(merchants)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        return
    cursor.execute("ALTER TABLE merchants ADD COLUMN user_id TEXT DEFAULT 'local'")
    cursor.execute("UPDATE merchants SET user_id = ? WHERE user_id IS NULL", (DEFAULT_USER_ID,))
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_merchants_user_name ON merchants(user_id, normalized_name)")
    conn.commit()


def save_expense(
    date: str,
    category: str,
    amount: float,
    currency: str,
    raw_text: str,
    *,
    merchant: str = None,
    subcategory: str = None,
    source_type: str = None,
    confidence_score: float = None,
    is_verified: int = 1,
    extracted_json: str = None,
    correction_json: str = None,
    user_id: str = None,
) -> int:
    """Save expense to database. user_id defaults to current context."""
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expenses)")
    has_user = any(row[1] == "user_id" for row in cursor.fetchall())
    if has_user:
        cursor.execute(
            """
            INSERT INTO expenses (
                date, category, amount, currency, raw_text,
                merchant, subcategory, source_type, confidence_score, is_verified, extracted_json, correction_json, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                category,
                amount,
                currency,
                raw_text,
                merchant,
                subcategory,
                source_type,
                confidence_score,
                is_verified,
                extracted_json,
                correction_json,
                uid,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO expenses (
                date, category, amount, currency, raw_text,
                merchant, subcategory, source_type, confidence_score, is_verified, extracted_json, correction_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                category,
                amount,
                currency,
                raw_text,
                merchant,
                subcategory,
                source_type,
                confidence_score,
                is_verified,
                extracted_json,
                correction_json,
            ),
        )
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


def _expense_user_clause(cursor, param_list: list, user_id: str = None) -> str:
    """Return SQL fragment AND (user_id = ? OR user_id IS NULL) and append param if expenses has user_id."""
    cursor.execute("PRAGMA table_info(expenses)")
    if not any(row[1] == "user_id" for row in cursor.fetchall()):
        return ""
    param_list.append(_resolve_user_id(user_id))
    return " AND (user_id = ? OR user_id IS NULL) "

def get_monthly_expenses(year: int, month: int, user_id: str = None) -> List[Dict]:
    """Get all expenses for a specific month (scoped to user when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    date_pattern = f"{year}-{month:02d}%"
    params = [date_pattern]
    user_clause = _expense_user_clause(cursor, params, user_id)
    cursor.execute(
        f"SELECT * FROM expenses WHERE date LIKE ?{user_clause}ORDER BY date DESC",
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_expenses_by_date_range(start_date: str, end_date: str, user_id: str = None) -> List[Dict]:
    """Get expenses where date in range (scoped to user when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = [start_date[:10], end_date[:10]]
    user_clause = _expense_user_clause(cursor, params, user_id)
    cursor.execute(
        f"SELECT * FROM expenses WHERE date >= ? AND date <= ?{user_clause}ORDER BY date DESC",
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def query_expenses_safe(
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    merchant_like: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    limit: int = 100,
    order_by: str = "date DESC",
    user_id: str = None,
) -> List[Dict]:
    """Safe parameterized query over expenses (scoped to user when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    conditions = []
    params = []
    if start_date:
        conditions.append("date >= ?")
        params.append(start_date[:10])
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date[:10])
    if category:
        conditions.append("LOWER(TRIM(category)) = ?")
        params.append(category.strip().lower())
    if merchant_like:
        conditions.append("(merchant IS NOT NULL AND LOWER(merchant) LIKE ?)")
        params.append("%" + merchant_like.strip().lower().replace("%", "").replace("_", "") + "%")
    if min_amount is not None:
        conditions.append("amount >= ?")
        params.append(min_amount)
    if max_amount is not None:
        conditions.append("amount <= ?")
        params.append(max_amount)
    user_clause = _expense_user_clause(cursor, params, user_id)
    where = " AND ".join(conditions) if conditions else "1=1"
    where = where + user_clause.strip()
    allowed_order = {"date DESC": "date DESC", "date ASC": "date ASC", "amount DESC": "amount DESC", "amount ASC": "amount ASC"}
    order_clause = allowed_order.get(order_by, "date DESC")
    limit = max(1, min(500, int(limit)))
    sql = f"SELECT * FROM expenses WHERE {where} ORDER BY {order_clause} LIMIT ?"
    params.append(limit)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_expenses(user_id: str = None) -> List[Dict]:
    """Get all expenses (scoped to user when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = []
    user_clause = _expense_user_clause(cursor, params, user_id)
    sql = f"SELECT * FROM expenses WHERE 1=1{user_clause}ORDER BY date DESC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_expenses_for_review(confidence_threshold: float = 0.6, user_id: str = None) -> List[Dict]:
    """Expenses needing verification (scoped to user when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = [confidence_threshold]
    user_clause = _expense_user_clause(cursor, params, user_id)
    cursor.execute(
        f"""
        SELECT * FROM expenses
        WHERE (is_verified = 0 OR is_verified IS NULL OR confidence_score IS NULL OR confidence_score < ?){user_clause}
        ORDER BY created_at DESC
        """,
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


_ALLOWED_EXPENSE_UPDATE_COLUMNS = {
    "date", "category", "amount", "currency", "raw_text",
    "merchant", "subcategory", "source_type", "confidence_score",
    "is_verified", "extracted_json", "correction_json",
}


def update_expense(expense_id: int, **kwargs) -> None:
    """Update an expense by ID. Only allowed columns are updated."""
    to_set = {k: v for k, v in kwargs.items() if k in _ALLOWED_EXPENSE_UPDATE_COLUMNS}
    if not to_set:
        return
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    placeholders = ", ".join(f"{k} = ?" for k in to_set)
    values = [to_set[k] for k in to_set]
    cursor.execute(f"UPDATE expenses SET {placeholders} WHERE id = ?", values + [expense_id])
    conn.commit()
    conn.close()


def delete_expense(expense_id: int) -> bool:
    """Delete an expense by ID. Returns True if a row was deleted."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ---------- Recurring expenses (insights) ----------

def _recurring_user_clause(cursor, params: list, user_id: str = None) -> str:
    cursor.execute("PRAGMA table_info(recurring_expenses)")
    if not any(row[1] == "user_id" for row in cursor.fetchall()):
        return ""
    params.append(_resolve_user_id(user_id))
    return " AND (user_id = ? OR user_id IS NULL) "

def get_recurring_expenses(user_id: str = None) -> List[Dict]:
    """Return detected recurring expenses (user-scoped when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = []
    user_clause = _recurring_user_clause(cursor, params, user_id)
    cursor.execute(
        f"SELECT * FROM recurring_expenses WHERE status = 'active'{user_clause}ORDER BY last_seen_date DESC",
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_recurring_expenses(user_id: str = None) -> None:
    """Remove recurring expense rows (user-scoped when column exists; default = current user)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(recurring_expenses)")
    has_user = any(row[1] == "user_id" for row in cursor.fetchall())
    if has_user:
        uid = _resolve_user_id(user_id)
        cursor.execute("DELETE FROM recurring_expenses WHERE user_id = ? OR user_id IS NULL", (uid,))
    else:
        cursor.execute("DELETE FROM recurring_expenses")
    conn.commit()
    conn.close()


def insert_recurring_expense(
    merchant: Optional[str],
    category: str,
    subcategory: Optional[str],
    typical_amount: float,
    currency: str,
    frequency_type: str,
    confidence_score: Optional[float],
    last_seen_date: Optional[str],
    next_expected_date: Optional[str],
    expense_count: int,
    status: str = "active",
    user_id: str = None,
) -> int:
    """Insert one recurring expense row. Returns new id."""
    uid = _resolve_user_id(user_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(recurring_expenses)")
    has_user = any(row[1] == "user_id" for row in cursor.fetchall())
    if has_user:
        cursor.execute(
            """
            INSERT INTO recurring_expenses (
                merchant, category, subcategory, typical_amount, currency,
                frequency_type, confidence_score, last_seen_date, next_expected_date,
                expense_count, status, updated_at, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                merchant,
                category,
                subcategory,
                typical_amount,
                currency or "USD",
                frequency_type,
                confidence_score,
                last_seen_date,
                next_expected_date,
                expense_count,
                status,
                now,
                uid,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO recurring_expenses (
                merchant, category, subcategory, typical_amount, currency,
                frequency_type, confidence_score, last_seen_date, next_expected_date,
                expense_count, status, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                merchant,
                category,
                subcategory,
                typical_amount,
                currency or "USD",
                frequency_type,
                confidence_score,
                last_seen_date,
                next_expected_date,
                expense_count,
                status,
                now,
            ),
        )
    rid = cursor.lastrowid
    conn.commit()
    conn.close()
    return rid


# ---------- Financial goals ----------

def _goals_user_clause(cursor, params: list, user_id: str = None) -> str:
    cursor.execute("PRAGMA table_info(financial_goals)")
    if not any(row[1] == "user_id" for row in cursor.fetchall()):
        return ""
    params.append(_resolve_user_id(user_id))
    return " AND (user_id = ? OR user_id IS NULL) "

def get_goals(status: str = "active", user_id: str = None) -> List[Dict]:
    """Return goals (default active only; user-scoped when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if status:
        params = [status]
        user_clause = _goals_user_clause(cursor, params, user_id)
        cursor.execute(f"SELECT * FROM financial_goals WHERE status = ?{user_clause}ORDER BY created_at DESC", params)
    else:
        params = []
        user_clause = _goals_user_clause(cursor, params, user_id)
        cursor.execute(f"SELECT * FROM financial_goals WHERE 1=1{user_clause}ORDER BY created_at DESC", params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_goal(goal_id: int, user_id: str = None) -> Optional[Dict]:
    """Return single goal by id (user-scoped when user_id column exists)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    params = [goal_id]
    user_clause = _goals_user_clause(cursor, params, user_id)
    cursor.execute(f"SELECT * FROM financial_goals WHERE id = ?{user_clause}", params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_goal(
    goal_type: str,
    target_amount: float,
    current_amount: float = 0,
    target_date: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "active",
    user_id: str = None,
) -> int:
    """Insert a goal. Returns new id."""
    uid = _resolve_user_id(user_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(financial_goals)")
    has_user = any(row[1] == "user_id" for row in cursor.fetchall())
    if has_user:
        cursor.execute(
            """
            INSERT INTO financial_goals (goal_type, target_amount, current_amount, target_date, category, description, status, updated_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (goal_type, target_amount, current_amount, target_date, category, description or "", status, now, uid),
        )
    else:
        cursor.execute(
            """
            INSERT INTO financial_goals (goal_type, target_amount, current_amount, target_date, category, description, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (goal_type, target_amount, current_amount, target_date, category, description or "", status, now),
        )
    gid = cursor.lastrowid
    conn.commit()
    conn.close()
    return gid


def update_goal(goal_id: int, **kwargs) -> bool:
    """Update goal by id. Allowed: goal_type, target_amount, current_amount, target_date, category, description, status."""
    allowed = {"goal_type", "target_amount", "current_amount", "target_date", "category", "description", "status"}
    to_set = {k: v for k, v in kwargs.items() if k in allowed}
    if not to_set:
        return False
    to_set["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    placeholders = ", ".join(f"{k} = ?" for k in to_set)
    values = [to_set[k] for k in to_set]
    cursor.execute(f"UPDATE financial_goals SET {placeholders} WHERE id = ?", values + [goal_id])
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_goal(goal_id: int) -> bool:
    """Delete goal by id."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM financial_goals WHERE id = ?", (goal_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ---------- Expense limits ----------

def get_limits(user_id: str = None) -> List[Dict]:
    """Get all expense limits for user (category -> amount)."""
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expense_limits)")
    cols = [row[1] for row in cursor.fetchall()]
    conn.close()
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if "user_id" in cols:
        cursor.execute("SELECT category, amount, currency FROM expense_limits WHERE user_id = ?", (uid,))
    else:
        cursor.execute("SELECT category, amount, currency FROM expense_limits")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_limit(category: str, amount: float, currency: str = "USD", user_id: str = None) -> None:
    """Set or update limit for a category (user-scoped when user_id column exists)."""
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expense_limits)")
    cols = [row[1] for row in cursor.fetchall()]
    if "user_id" in cols:
        cursor.execute(
            "INSERT INTO expense_limits (user_id, category, amount, currency) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, category) DO UPDATE SET amount = ?, currency = ?",
            (uid, category, amount, currency, amount, currency),
        )
    else:
        cursor.execute(
            "INSERT INTO expense_limits (category, amount, currency) VALUES (?, ?, ?) "
            "ON CONFLICT(category) DO UPDATE SET amount = ?, currency = ?",
            (category, amount, currency, amount, currency),
        )
    conn.commit()
    conn.close()


def delete_limit(category: str, user_id: str = None) -> bool:
    """Remove limit for category. Returns True if deleted."""
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(expense_limits)")
    cols = [row[1] for row in cursor.fetchall()]
    if "user_id" in cols:
        cursor.execute("DELETE FROM expense_limits WHERE user_id = ? AND category = ?", (uid, category))
    else:
        cursor.execute("DELETE FROM expense_limits WHERE category = ?", (category,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_spending_by_category_for_month(year: int, month: int, user_id: str = None) -> Dict[str, float]:
    """Return { category: total_amount, 'total': sum } for the given month (user-scoped)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    date_pattern = f"{year}-{month:02d}%"
    params = [date_pattern]
    user_clause = _expense_user_clause(cursor, params, user_id)
    cursor.execute(
        f"SELECT category, SUM(amount) AS total FROM expenses WHERE date LIKE ?{user_clause}GROUP BY category",
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    by_cat = {row[0]: float(row[1]) for row in rows}
    by_cat["total"] = sum(by_cat.values())
    return by_cat


def get_spending_by_category_until_day(year: int, month: int, end_day: int, user_id: str = None) -> Dict[str, float]:
    """Spend from 1st through end_day in year-month (user-scoped)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{min(31, max(1, end_day)):02d}"
    params = [start_date, end_date]
    user_clause = _expense_user_clause(cursor, params, user_id)
    cursor.execute(
        f"""SELECT category, SUM(amount) AS total FROM expenses
           WHERE date >= ? AND date <= ?{user_clause}GROUP BY category""",
        params,
    )
    rows = cursor.fetchall()
    conn.close()
    by_cat = {row[0]: float(row[1]) for row in rows}
    by_cat["total"] = sum(by_cat.values())
    return by_cat


# ---------- Gmail processed (deduplication) ----------

def gmail_is_processed(message_id: str, user_id: str = None) -> bool:
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(gmail_processed)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        cursor.execute("SELECT 1 FROM gmail_processed WHERE message_id = ? AND (user_id = ? OR user_id IS NULL)", (message_id, uid))
    else:
        cursor.execute("SELECT 1 FROM gmail_processed WHERE message_id = ?", (message_id,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


def gmail_mark_processed(message_id: str, user_id: str = None) -> None:
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(gmail_processed)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        cursor.execute("INSERT OR IGNORE INTO gmail_processed (message_id, user_id) VALUES (?, ?)", (message_id, uid))
    else:
        cursor.execute("INSERT OR IGNORE INTO gmail_processed (message_id) VALUES (?)", (message_id,))
    conn.commit()
    conn.close()


# ---------- Merchant memory ----------

def get_merchant_by_normalized_name(normalized_name: str, user_id: str = None) -> Optional[Dict]:
    """Look up merchant by normalized name (user-scoped when user_id column exists)."""
    if not normalized_name or not normalized_name.strip():
        return None
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    name = normalized_name.strip().lower()
    cursor.execute("PRAGMA table_info(merchants)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        uid = _resolve_user_id(user_id)
        cursor.execute(
            "SELECT id, normalized_name, display_name, default_category, subcategory, use_count FROM merchants WHERE normalized_name = ? AND (user_id = ? OR user_id IS NULL)",
            (name, uid),
        )
    else:
        cursor.execute(
            "SELECT id, normalized_name, display_name, default_category, subcategory, use_count FROM merchants WHERE normalized_name = ?",
            (name,),
        )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_merchant_by_alias(alias_text: str, user_id: str = None) -> Optional[Dict]:
    """Look up merchant by alias (user-scoped when merchants.user_id exists)."""
    if not alias_text or not alias_text.strip():
        return None
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(merchants)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        uid = _resolve_user_id(user_id)
        cursor.execute(
            "SELECT m.id, m.normalized_name, m.display_name, m.default_category, m.subcategory, m.use_count "
            "FROM merchants m JOIN merchant_aliases a ON m.id = a.merchant_id WHERE a.alias_text = ? AND (m.user_id = ? OR m.user_id IS NULL)",
            (alias_text.strip().lower(), uid),
        )
    else:
        cursor.execute(
            "SELECT m.id, m.normalized_name, m.display_name, m.default_category, m.subcategory, m.use_count "
            "FROM merchants m JOIN merchant_aliases a ON m.id = a.merchant_id WHERE a.alias_text = ?",
            (alias_text.strip().lower(),),
        )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_merchant(
    normalized_name: str,
    default_category: str,
    display_name: str = None,
    subcategory: str = None,
    user_id: str = None,
) -> int:
    """Insert or ignore merchant; return merchant id (user-scoped when user_id column exists)."""
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    name = normalized_name.strip().lower()
    cursor.execute("PRAGMA table_info(merchants)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        cursor.execute(
            "INSERT INTO merchants (normalized_name, display_name, default_category, subcategory, user_id) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, normalized_name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP",
            (name, display_name or name, default_category, subcategory, uid),
        )
        cursor.execute("SELECT id FROM merchants WHERE normalized_name = ? AND user_id = ?", (name, uid))
    else:
        cursor.execute(
            "INSERT INTO merchants (normalized_name, display_name, default_category, subcategory) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(normalized_name) DO UPDATE SET updated_at = CURRENT_TIMESTAMP",
            (name, display_name or name, default_category, subcategory),
        )
        cursor.execute("SELECT id FROM merchants WHERE normalized_name = ?", (name,))
    merchant_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return merchant_id


def update_merchant_category_conservative(
    normalized_name: str,
    category: str,
    subcategory: str = None,
    confidence_score: float = 0.0,
    min_confidence_to_overwrite: float = 0.85,
    min_use_count_to_protect: int = 3,
    user_id: str = None,
) -> bool:
    """
    Update merchant's default_category only if conservative rules allow (user-scoped when user_id column exists).
    Returns True if updated.
    """
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    name = normalized_name.strip().lower()
    cursor.execute("PRAGMA table_info(merchants)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        uid = _resolve_user_id(user_id)
        cursor.execute("SELECT id, default_category, subcategory, use_count FROM merchants WHERE normalized_name = ? AND (user_id = ? OR user_id IS NULL)", (name, uid))
    else:
        cursor.execute("SELECT id, default_category, subcategory, use_count FROM merchants WHERE normalized_name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    merchant_id, current_cat, current_sub, use_count = row[0], row[1], row[2] or "", row[3] or 0
    if current_cat == category and (current_sub or "") == (subcategory or ""):
        conn.close()
        return False
    if use_count >= min_use_count_to_protect and confidence_score < min_confidence_to_overwrite:
        conn.close()
        return False
    if use_count < min_use_count_to_protect and confidence_score < 0.75:
        conn.close()
        return False
    cursor.execute(
        "UPDATE merchants SET default_category = ?, subcategory = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (category, subcategory, merchant_id),
    )
    conn.commit()
    conn.close()
    return True


def increment_merchant_use_count(normalized_name: str, user_id: str = None) -> None:
    """Increment use_count for merchant (user-scoped when user_id column exists)."""
    if not normalized_name or not normalized_name.strip():
        return
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    name = normalized_name.strip().lower()
    cursor.execute("PRAGMA table_info(merchants)")
    if any(row[1] == "user_id" for row in cursor.fetchall()):
        uid = _resolve_user_id(user_id)
        cursor.execute(
            "UPDATE merchants SET use_count = use_count + 1, updated_at = CURRENT_TIMESTAMP WHERE normalized_name = ? AND (user_id = ? OR user_id IS NULL)",
            (name, uid),
        )
    else:
        cursor.execute(
            "UPDATE merchants SET use_count = use_count + 1, updated_at = CURRENT_TIMESTAMP WHERE normalized_name = ?",
            (name,),
        )
    conn.commit()
    conn.close()


def add_merchant_alias(merchant_id: int, alias_text: str) -> None:
    """Add an alias for a merchant (alias_text normalized to lowercase)."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO merchant_aliases (merchant_id, alias_text) VALUES (?, ?)",
        (merchant_id, alias_text.strip().lower()),
    )
    conn.commit()
    conn.close()


def clear_all_data(user_id: str = None) -> dict:
    """
    Delete all expenses, limits, goals, and recurring data for the given user.
    Returns counts of deleted rows: { "expenses": N, "limits": N, "goals": N, "recurring": N, "gmail_processed": N }.
    """
    uid = _resolve_user_id(user_id)
    conn = sqlite3.connect(DATABASE_PATH, timeout=SQLITE_TIMEOUT)
    cursor = conn.cursor()
    counts = {}

    def has_column(table: str, col: str) -> bool:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == col for row in cursor.fetchall())

    # Expenses
    if has_column("expenses", "user_id"):
        cursor.execute("DELETE FROM expenses WHERE user_id = ? OR user_id IS NULL", (uid,))
    else:
        cursor.execute("DELETE FROM expenses")
    counts["expenses"] = cursor.rowcount

    # Limits
    if has_column("expense_limits", "user_id"):
        cursor.execute("DELETE FROM expense_limits WHERE user_id = ?", (uid,))
    else:
        cursor.execute("DELETE FROM expense_limits")
    counts["limits"] = cursor.rowcount

    # Goals
    if has_column("financial_goals", "user_id"):
        cursor.execute("DELETE FROM financial_goals WHERE user_id = ? OR user_id IS NULL", (uid,))
    else:
        cursor.execute("DELETE FROM financial_goals")
    counts["goals"] = cursor.rowcount

    # Recurring
    if has_column("recurring_expenses", "user_id"):
        cursor.execute("DELETE FROM recurring_expenses WHERE user_id = ? OR user_id IS NULL", (uid,))
    else:
        cursor.execute("DELETE FROM recurring_expenses")
    counts["recurring"] = cursor.rowcount

    # Gmail processed (so next sync can re-process if desired)
    if has_column("gmail_processed", "user_id"):
        cursor.execute("DELETE FROM gmail_processed WHERE user_id = ? OR user_id IS NULL", (uid,))
    else:
        cursor.execute("DELETE FROM gmail_processed")
    counts["gmail_processed"] = cursor.rowcount

    conn.commit()
    conn.close()
    return counts
