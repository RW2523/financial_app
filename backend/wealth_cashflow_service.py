"""
Wealth Hub: cashflow allocation from salary, expenses, and investments.
"""
from datetime import datetime
from typing import Dict, Any
import database

# Categories often considered "fixed" (obligations)
FIXED_CATEGORY_NAMES = {"rent", "mortgage", "utilities", "insurance", "loan", "loans", "subscription", "subscriptions"}


def get_cashflow_summary(year: int = None, month: int = None, user_id: str = None) -> Dict[str, Any]:
    """
    total_income, total_expenses, total_invested, net_savings, free_cash,
    savings_ratio, investment_ratio, expense_ratio,
    safe_investable_surplus, aggressive_investable_surplus, remaining_buffer,
    fixed_expenses, variable_expenses (when derivable),
    mom_*: previous month and deltas for income, expenses, invested, savings.
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    uid = user_id

    # Income: salary for this month
    salary_summary = database.get_monthly_income_summary(y, m, user_id=uid)
    total_income = salary_summary["net_income"] + salary_summary["bonus_total"]

    # Expenses: from expenses table
    spending = database.get_spending_by_category_for_month(y, m, user_id=uid)
    total_expenses = spending.get("total", 0) or 0

    # Fixed vs variable (heuristic: category name contains fixed keywords)
    fixed_expenses = 0.0
    variable_expenses = 0.0
    for cat, amt in spending.items():
        if cat == "total" or not amt:
            continue
        cat_lower = (cat or "").lower()
        if any(f in cat_lower for f in FIXED_CATEGORY_NAMES):
            fixed_expenses += amt
        else:
            variable_expenses += amt
    if fixed_expenses == 0 and variable_expenses == 0 and total_expenses > 0:
        fixed_expenses = total_expenses * 0.5
        variable_expenses = total_expenses * 0.5

    # Invested this month
    transactions = database.list_investment_transactions(user_id=uid)
    pattern = f"{y}-{m:02d}"
    total_invested = 0.0
    for t in transactions:
        if (t.get("date") or "")[:7] != pattern:
            continue
        if (t.get("transaction_type") or "").upper() == "BUY":
            total_invested += float(t.get("quantity") or 0) * float(t.get("price") or 0) + float(t.get("fees") or 0)

    net_savings = total_income - total_expenses
    free_cash = net_savings - total_invested
    savings_ratio = (net_savings / total_income * 100) if total_income else 0
    investment_ratio = (total_invested / total_income * 100) if total_income else 0
    expense_ratio = (total_expenses / total_income * 100) if total_income else 0

    # Investable surplus: safe (50% of free_cash), aggressive (80%), remaining buffer
    safe_investable = free_cash * 0.5 if free_cash > 0 else 0.0
    aggressive_investable = free_cash * 0.8 if free_cash > 0 else 0.0
    remaining_buffer = free_cash - aggressive_investable if free_cash > 0 else 0.0

    # Month-over-month: previous month
    if m == 1:
        prev_y, prev_m = y - 1, 12
    else:
        prev_y, prev_m = y, m - 1
    prev_salary = database.get_monthly_income_summary(prev_y, prev_m, user_id=uid)
    prev_income = prev_salary["net_income"] + prev_salary["bonus_total"]
    prev_spending = database.get_spending_by_category_for_month(prev_y, prev_m, user_id=uid)
    prev_expenses = prev_spending.get("total", 0) or 0
    prev_pattern = f"{prev_y}-{prev_m:02d}"
    prev_invested = 0.0
    for t in transactions:
        if (t.get("date") or "")[:7] != prev_pattern:
            continue
        if (t.get("transaction_type") or "").upper() == "BUY":
            prev_invested += float(t.get("quantity") or 0) * float(t.get("price") or 0) + float(t.get("fees") or 0)
    prev_savings = prev_income - prev_expenses

    return {
        "year": y,
        "month": m,
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "total_invested": round(total_invested, 2),
        "net_savings": round(net_savings, 2),
        "free_cash": round(free_cash, 2),
        "savings_ratio": round(savings_ratio, 2),
        "investment_ratio": round(investment_ratio, 2),
        "expense_ratio": round(expense_ratio, 2),
        "safe_investable_surplus": round(safe_investable, 2),
        "aggressive_investable_surplus": round(aggressive_investable, 2),
        "remaining_buffer": round(remaining_buffer, 2),
        "fixed_expenses": round(fixed_expenses, 2),
        "variable_expenses": round(variable_expenses, 2),
        "mom_previous_income": round(prev_income, 2),
        "mom_previous_expenses": round(prev_expenses, 2),
        "mom_previous_invested": round(prev_invested, 2),
        "mom_previous_savings": round(prev_savings, 2),
        "mom_delta_income": round(total_income - prev_income, 2),
        "mom_delta_expenses": round(total_expenses - prev_expenses, 2),
        "mom_delta_invested": round(total_invested - prev_invested, 2),
        "mom_delta_savings": round(net_savings - prev_savings, 2),
    }
