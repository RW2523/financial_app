"""
Wealth Hub: grounded suggestions from app data only. No generic advice.
"""
from datetime import datetime
from typing import Dict, Any, List
import wealth_cashflow_service as cf
import wealth_portfolio_service as ps

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"

ROUTES = {
    "cashflow": "/wealth/cashflow",
    "manager": "/wealth/manager",
}


def _suggestion(
    suggestion_id: str,
    title: str,
    message: str,
    why_this_matters: str,
    destination: str,
    metric: str,
    value: float,
    severity: str,
) -> Dict[str, Any]:
    return {
        "id": suggestion_id,
        "title": title,
        "message": message,
        "why_this_matters": why_this_matters,
        "destination": destination,
        "metric": metric,
        "value": value,
        "severity": severity,
    }


def get_suggestions(year: int = None, month: int = None, user_id: str = None) -> Dict[str, Any]:
    """
    Returns list of { id, title, message, metric, value, severity }.
    All tied to deterministic metrics.
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    uid = user_id
    suggestions: List[Dict[str, Any]] = []

    cashflow = cf.get_cashflow_summary(y, m, user_id=uid)
    portfolio = ps.get_portfolio_summary(user_id=uid)

    # Expense ratio too high relative to income (e.g. > 80%)
    expense_ratio = cashflow.get("expense_ratio") or 0
    if cashflow.get("total_income", 0) > 0 and expense_ratio > 80:
        suggestions.append(_suggestion(
            "expense_ratio_high",
            "Expense ratio high",
            f"Expenses are {expense_ratio:.1f}% of income this month. Consider reducing non-essential spending to increase savings.",
            "A high expense ratio leaves little room for savings and investing; small income shocks can strain your buffer.",
            ROUTES["cashflow"],
            "expense_ratio",
            expense_ratio,
            SEVERITY_HIGH if expense_ratio > 95 else SEVERITY_MEDIUM,
        ))

    # Free cash buffer low after investments
    free_cash = cashflow.get("free_cash") or 0
    total_income = cashflow.get("total_income") or 0
    if total_income > 0 and free_cash < 0:
        suggestions.append(_suggestion(
            "free_cash_negative",
            "Free cash is negative",
            "Investments and expenses exceed income this month. Consider reducing investment amount or expenses to maintain a buffer.",
            "Negative free cash means you are drawing down savings or going into debt to cover spending and investments.",
            ROUTES["cashflow"],
            "free_cash",
            free_cash,
            SEVERITY_HIGH,
        ))
    elif total_income > 0 and free_cash < total_income * 0.1:
        suggestions.append(_suggestion(
            "free_cash_low",
            "Free cash buffer low",
            f"Free cash ({free_cash:.0f}) is less than 10% of income. Keeping a larger buffer can help with unexpected expenses.",
            "A small buffer increases stress when income is delayed or an emergency expense appears.",
            ROUTES["cashflow"],
            "free_cash",
            free_cash,
            SEVERITY_MEDIUM,
        ))

    # Investment concentration too high in one stock
    holdings = portfolio.get("holdings") or []
    total_value = portfolio.get("total_current_value") or 0
    if total_value > 0 and holdings:
        top = holdings[0]
        top_value = top.get("current_value") or top.get("total_invested") or 0
        concentration = (top_value / total_value) * 100
        if concentration > 50:
            suggestions.append(_suggestion(
                "concentration_high",
                "Portfolio concentration high",
                f"{top.get('ticker', '')} is {concentration:.1f}% of portfolio. Consider diversifying to reduce single-stock risk.",
                "Concentration in one stock amplifies volatility and company-specific risk.",
                ROUTES["manager"],
                "concentration_pct",
                round(concentration, 1),
                SEVERITY_MEDIUM if concentration < 70 else SEVERITY_HIGH,
            ))

    # Current spending patterns reducing investable surplus
    savings_ratio = cashflow.get("savings_ratio") or 0
    if total_income > 0 and savings_ratio < 10 and total_income > 1000:
        suggestions.append(_suggestion(
            "savings_ratio_low",
            "Low savings ratio",
            f"Savings ratio is {savings_ratio:.1f}%. Increasing savings can grow your investable surplus over time.",
            "Low savings slow progress toward goals and leave little to invest when opportunities arise.",
            ROUTES["cashflow"],
            "savings_ratio",
            savings_ratio,
            SEVERITY_MEDIUM,
        ))

    # Recurring expenses limiting savings (simplified: high expense ratio + many categories)
    if expense_ratio > 70 and savings_ratio < 20 and total_income > 0:
        suggestions.append(_suggestion(
            "recurring_limiting_savings",
            "Spending may be limiting savings growth",
            "A high portion of income goes to expenses. Review recurring subscriptions and fixed costs to free up capacity for savings.",
            "Trimming fixed or recurring costs can free up a predictable amount each month for goals.",
            ROUTES["cashflow"],
            "expense_ratio",
            expense_ratio,
            SEVERITY_LOW,
        ))

    return {
        "year": y,
        "month": m,
        "suggestions": suggestions,
    }
