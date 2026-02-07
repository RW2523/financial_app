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
