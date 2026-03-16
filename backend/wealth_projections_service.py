"""
Wealth Hub: deterministic projections from salary, expense, and investment history.
Modes: no_growth, conservative, moderate, aggressive. Scenario support and multiple views.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import database

# Annual return assumptions (decimal) per mode for portfolio projection
PROJECTION_MODES = {
    "no_growth": 0.0,
    "conservative": 0.04,
    "moderate": 0.07,
    "aggressive": 0.10,
}


def _avg_monthly_income(uid: str, months_back: int = 6) -> float:
    now = datetime.now()
    total = 0.0
    n = 0
    for i in range(months_back):
        if now.month <= i:
            y, m = now.year - 1, now.month - i + 12
        else:
            y, m = now.year, now.month - i
        s = database.get_monthly_income_summary(y, m, user_id=uid)
        if s["net_income"] or s["bonus_total"]:
            total += s["net_income"] + s["bonus_total"]
            n += 1
    return total / n if n else 0.0


def _avg_monthly_expenses(uid: str, months_back: int = 6) -> float:
    now = datetime.now()
    total = 0.0
    n = 0
    for i in range(months_back):
        if now.month <= i:
            y, m = now.year - 1, now.month - i + 12
        else:
            y, m = now.year, now.month - i
        spending = database.get_spending_by_category_for_month(y, m, user_id=uid)
        t = spending.get("total", 0) or 0
        if t > 0:
            total += t
            n += 1
    return total / n if n else 0.0


def _avg_monthly_invested(uid: str, months_back: int = 6) -> float:
    transactions = database.list_investment_transactions(user_id=uid)
    by_month: Dict[str, float] = {}
    for t in transactions:
        if (t.get("transaction_type") or "").upper() != "BUY":
            continue
        date_str = t.get("date") or ""
        key = date_str[:7]
        if not key:
            continue
        amt = float(t.get("quantity") or 0) * float(t.get("price") or 0) + float(t.get("fees") or 0)
        by_month[key] = by_month.get(key, 0) + amt
    if not by_month:
        return 0.0
    return sum(by_month.values()) / len(by_month)


def get_projections(
    year: int = None,
    month: int = None,
    user_id: str = None,
    portfolio_growth_mode: str = "moderate",
    monthly_investment_override: Optional[float] = None,
    expense_growth_pct: Optional[float] = None,
    salary_growth_pct: Optional[float] = None,
    target_buffer: Optional[float] = None,
) -> Dict[str, Any]:
    """
    projected_end_of_month_expenses, projected_monthly_surplus, projected_yearly_invested,
    portfolio_projection { 6m, 1y, 3y }, scenarios (current_pace, disciplined_spending, increased_investing, reduced_expenses).
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    uid = user_id
    mode = portfolio_growth_mode or "moderate"
    annual_return = PROJECTION_MODES.get(mode, PROJECTION_MODES["moderate"])

    # Projected end-of-month expenses
    try:
        import forecast_service as fs
        proj = fs.projected_month_end(y, m)
        projected_eom_expenses = proj.get("projected_total", 0) or 0
    except Exception:
        spending = database.get_spending_by_category_for_month(y, m, user_id=uid)
        projected_eom_expenses = spending.get("total", 0) or 0

    avg_income = _avg_monthly_income(uid)
    avg_expenses = _avg_monthly_expenses(uid)
    projected_monthly_surplus = avg_income - (projected_eom_expenses or avg_expenses)
    avg_invested = _avg_monthly_invested(uid)
    if monthly_investment_override is not None:
        avg_invested = monthly_investment_override
    projected_yearly_invested = avg_invested * 12

    # Apply growth assumptions for scenario math
    expense_mult = 1 + (expense_growth_pct or 0) / 100
    salary_mult = 1 + (salary_growth_pct or 0) / 100

    # Portfolio value today
    try:
        import wealth_portfolio_service as wps
        summary = wps.get_portfolio_summary(user_id=uid)
        current_portfolio_value = summary["total_current_value"]
    except Exception:
        current_portfolio_value = 0.0

    def future_value(pv: float, monthly_inv: float, months: int, r_annual: float) -> float:
        """FV with monthly contributions: FV = PV*(1+r)^n + PMT * (((1+r)^n - 1) / r)."""
        if months <= 0:
            return pv
        r = r_annual / 12
        fv_pv = pv * ((1 + r) ** months)
        if r > 0 and monthly_inv > 0:
            fv_pmt = monthly_inv * (((1 + r) ** months - 1) / r)
            return fv_pv + fv_pmt
        return fv_pv + monthly_inv * months

    portfolio_projection = {
        "6m": round(future_value(current_portfolio_value, avg_invested, 6, annual_return), 2),
        "1y": round(future_value(current_portfolio_value, avg_invested, 12, annual_return), 2),
        "3y": round(future_value(current_portfolio_value, avg_invested, 36, annual_return), 2),
    }

    # Multiple scenarios
    base_surplus = projected_monthly_surplus
    base_exp = projected_eom_expenses or avg_expenses
    scenarios = [
        {
            "id": "current_pace",
            "label": "Current pace",
            "description": "If you keep income, expenses, and investing as they are.",
            "projected_monthly_surplus": round(base_surplus, 2),
            "projected_yearly_invested": round(avg_invested * 12, 2),
            "portfolio_1y": round(future_value(current_portfolio_value, avg_invested, 12, annual_return), 2),
        },
        {
            "id": "disciplined_spending",
            "label": "Disciplined spending",
            "description": "10% lower expenses; same investing.",
            "projected_monthly_surplus": round(avg_income - base_exp * 0.9 - avg_invested, 2),
            "projected_yearly_invested": round(avg_invested * 12, 2),
            "portfolio_1y": round(future_value(current_portfolio_value, avg_invested, 12, annual_return), 2),
        },
        {
            "id": "increased_investing",
            "label": "Increased investing",
            "description": "20% more invested each month.",
            "projected_monthly_surplus": round(base_surplus - avg_invested * 0.2, 2),
            "projected_yearly_invested": round(avg_invested * 1.2 * 12, 2),
            "portfolio_1y": round(future_value(current_portfolio_value, avg_invested * 1.2, 12, annual_return), 2),
        },
        {
            "id": "reduced_expenses",
            "label": "Reduced expenses",
            "description": "15% lower expenses; surplus goes to buffer.",
            "projected_monthly_surplus": round(avg_income - base_exp * 0.85 - avg_invested, 2),
            "projected_yearly_invested": round(avg_invested * 12, 2),
            "portfolio_1y": round(future_value(current_portfolio_value, avg_invested, 12, annual_return), 2),
        },
    ]

    return {
        "year": y,
        "month": m,
        "projected_end_of_month_expenses": round(projected_eom_expenses, 2),
        "projected_monthly_surplus": round(projected_monthly_surplus, 2),
        "projected_yearly_invested": round(projected_yearly_invested, 2),
        "portfolio_projection": portfolio_projection,
        "portfolio_growth_mode": mode,
        "annual_return_assumption": annual_return,
        "current_portfolio_value": round(current_portfolio_value, 2),
        "scenarios": scenarios,
    }
