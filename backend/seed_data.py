"""
Seed sample expense data for a Master's student in Boston, US.
Covers every month of 2025 and January 2026.

Run from project root:
  python backend/seed_data.py
Or from backend directory:
  cd backend && python seed_data.py
"""
import sys
import os

# When run as script from project root (python backend/seed_data.py), add backend to path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend = _script_dir
if _backend not in sys.path:
    sys.path.insert(0, _backend)
_root = os.path.dirname(_backend)
if _root not in sys.path:
    sys.path.insert(0, _root)

import database

# Categories used in the app
CATEGORIES = ["food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other"]

# Template: (date_str, category, amount, raw_text)
# We'll generate per month with realistic Boston grad-student expenses

def generate_monthly_expenses(year: int, month: int) -> list:
    """Generate realistic expenses for one month for a Boston master's student."""
    import random
    expenses = []
    r = random.Random(year * 100 + month)  # deterministic per month

    # Rent (1st of month) - Boston shared room
    rent = r.randint(950, 1150)
    expenses.append((f"{year}-{month:02d}-01", "utilities", float(rent),
                     f"Rent for {month}/{year} - shared room Allston"))

    # Groceries - 3-4 entries per month
    for _ in range(r.randint(3, 4)):
        day = r.randint(2, 28)
        amt = round(r.uniform(35, 85), 2)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "food", amt,
                         f"Groceries at Trader Joe's / Star Market"))

    # Transport - T pass + occasional Uber
    t_pass_day = r.randint(1, 5)
    expenses.append((f"{year}-{month:02d}-{t_pass_day:02d}", "transport", 90.0,
                     "MBTA monthly pass"))
    for _ in range(r.randint(1, 3)):
        day = r.randint(5, 28)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "transport", round(r.uniform(12, 35), 2),
                         "Uber to campus / airport"))

    # Food - dining out / coffee
    for _ in range(r.randint(4, 8)):
        day = r.randint(1, 28)
        amt = round(r.uniform(8, 28), 2)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "food", amt,
                         "Coffee / lunch on campus / dinner out"))

    # Utilities - internet, phone, electric share
    expenses.append((f"{year}-{month:02d}-15", "utilities", round(r.uniform(35, 55), 2),
                     "Internet and phone"))
    if month in [7, 8, 12, 1, 2]:  # AC or heating
        expenses.append((f"{year}-{month:02d}-20", "utilities", round(r.uniform(40, 75), 2),
                         "Electric / gas (heating or AC)"))

    # Shopping - books, supplies, clothes
    for _ in range(r.randint(1, 2)):
        day = r.randint(3, 25)
        amt = round(r.uniform(25, 120), 2)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "shopping", amt,
                         "Books / supplies / clothes"))

    # Entertainment
    for _ in range(r.randint(2, 4)):
        day = r.randint(1, 28)
        amt = round(r.uniform(15, 45), 2)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "entertainment", amt,
                         "Movies / concert / bars with friends"))

    # Healthcare - occasional
    if r.random() < 0.4:
        day = r.randint(1, 28)
        amt = round(r.uniform(15, 80), 2)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "healthcare", amt,
                         "Pharmacy / copay / health supplies"))

    # Other - misc
    for _ in range(r.randint(0, 2)):
        day = r.randint(1, 28)
        amt = round(r.uniform(10, 50), 2)
        expenses.append((f"{year}-{month:02d}-{day:02d}", "other", amt,
                         "Miscellaneous"))

    return expenses


def get_sample_expenses_for_months(months: list = None):
    """
    Generate sample expenses for the given (year, month) list.
    If months is None, uses last 4 months including current.
    Returns list of (date_str, category, amount, raw_text).
    """
    from datetime import datetime
    if months is None:
        now = datetime.now()
        months = []
        for i in range(4):
            m = now.month - i
            y = now.year
            while m < 1:
                m += 12
                y -= 1
            months.append((y, m))
        months.reverse()
    out = []
    for year, month in months:
        for date_str, category, amount, raw_text in generate_monthly_expenses(year, month):
            out.append((date_str, category, amount, raw_text))
    return out


def _last_four_months_yyyymm():
    """Return list of (year, month) for last 4 months including current."""
    from datetime import datetime
    now = datetime.now()
    months = []
    for i in range(4):
        m = now.month - i
        y = now.year
        while m < 1:
            m += 12
            y -= 1
        months.append((y, m))
    months.reverse()
    return months


def load_sample_data(user_id: str = None) -> dict:
    """
    Load sample expenses (last 4 months), 4 limits, 2 goals, and Wealth Hub data:
    salary records, investment transactions, watchlist items, and a liability.
    Returns { "expenses": N, "limits": N, "goals": N, "salary_records": N, "investments": N, "watchlist": N, "liabilities": N }.
    """
    database.init_database()
    uid = database._resolve_user_id(user_id)
    expenses = get_sample_expenses_for_months()
    for date_str, category, amount, raw_text in expenses:
        database.save_expense(date_str, category, amount, "USD", raw_text, user_id=uid)
    # Limits that make sense with the generated spend
    database.set_limit("total", 3500.0, "USD", user_id=uid)
    database.set_limit("food", 600.0, "USD", user_id=uid)
    database.set_limit("transport", 200.0, "USD", user_id=uid)
    database.set_limit("utilities", 1200.0, "USD", user_id=uid)
    database.create_goal(
        "savings_target", 2000.0, 0, "2026-12-31", None,
        "Save for emergency fund", "active", user_id=uid
    )
    database.create_goal(
        "spending_reduction", 400.0, 0, "2026-06-30", "food",
        "Reduce monthly food spend to $400", "active", user_id=uid
    )

    # Wealth Hub: salary (monthly pay for last 4 months)
    months = _last_four_months_yyyymm()
    salary_count = 0
    for y, m in months:
        date_str = f"{y}-{m:02d}-01"
        database.create_salary_record(
            date=date_str,
            source="Employer (sample)",
            gross_amount=4200.0,
            deductions=520.0,
            net_amount=3680.0,
            bonus_amount=0 if m % 3 != 0 else 300.0,
            notes="Sample salary",
            user_id=uid,
        )
        salary_count += 1

    # Wealth Hub: investment transactions (BUY) so portfolio has holdings
    investments = [
        ("AAPL", "Apple Inc", "2025-11-01", 5, 175.0),
        ("AAPL", "Apple Inc", "2025-12-10", 3, 182.0),
        ("MSFT", "Microsoft Corp", "2025-11-15", 2, 380.0),
        ("GOOGL", "Alphabet Inc", "2025-12-01", 4, 140.0),
    ]
    for ticker, name, date_str, qty, price in investments:
        database.create_investment_transaction(
            ticker=ticker,
            stock_name=name,
            transaction_type="BUY",
            quantity=qty,
            price=price,
            fees=0,
            date=date_str,
            broker="Sample Broker",
            notes="Sample investment",
            user_id=uid,
        )
    investment_count = len(investments)

    # Wealth Hub: watchlist
    watchlist_items = [
        ("NVDA", "NVIDIA Corp", 120.0, "Tech"),
        ("AMZN", "Amazon.com Inc", 180.0, "Consumer"),
    ]
    for ticker, name, target, sector in watchlist_items:
        database.add_watchlist_item(
            ticker=ticker,
            stock_name=name,
            target_buy_price=target,
            sector=sector,
            user_id=uid,
        )
    watchlist_count = len(watchlist_items)

    # Wealth Hub: one liability (e.g. student loan)
    database.create_liability(
        name="Student loan (sample)",
        balance=12000.0,
        liability_type="education",
        notes="Sample liability for net worth",
        user_id=uid,
    )
    liability_count = 1

    return {
        "expenses": len(expenses),
        "limits": 4,
        "goals": 2,
        "salary_records": salary_count,
        "investments": investment_count,
        "watchlist": watchlist_count,
        "liabilities": liability_count,
    }


def main():
    database.init_database()

    total_added = 0
    months = (
        [(2025, m) for m in range(1, 13)] +
        [(2026, 1)]
    )

    for year, month in months:
        for date_str, category, amount, raw_text in generate_monthly_expenses(year, month):
            database.save_expense(date_str, category, amount, "USD", raw_text)
            total_added += 1

    print(f"✅ Inserted {total_added} sample expenses for Boston Master's student")
    print("   Months: Jan 2025 – Dec 2025, Jan 2026")
    print("   View in app: http://localhost:8501 → View Expenses / Monthly Summary")


if __name__ == "__main__":
    main()
