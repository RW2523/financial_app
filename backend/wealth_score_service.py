"""
Wealth Score / Money Health Score: deterministic 0-100 score from expense ratio,
savings ratio, free cash buffer, investment consistency, diversification, concentration, goal progress.
"""
from typing import Dict, Any
from datetime import datetime


def compute_wealth_score(user_id: str = None) -> Dict[str, Any]:
    """
    Returns score 0-100 and contributing factors (each 0-100 or weight).
    Formula is modular: weighted average of component scores.
    """
    now = datetime.now()
    y, m = now.year, now.month
    factors = {}
    weights = {}

    try:
        import wealth_cashflow_service as cf
        cashflow = cf.get_cashflow_summary(y, m, user_id=user_id)
    except Exception:
        cashflow = {}

    try:
        import wealth_portfolio_service as ps
        portfolio = ps.get_portfolio_summary(user_id=user_id)
    except Exception:
        portfolio = {}

    try:
        import wealth_stock_service as wss
        manager = wss.get_portfolio_manager_view(user_id=user_id)
    except Exception:
        manager = {}

    # Expense ratio: lower is better. <50% = 100, >90% = 0
    expense_ratio = cashflow.get("expense_ratio") or 0
    if cashflow.get("total_income", 0) <= 0:
        factors["expense_ratio"] = 100
    else:
        factors["expense_ratio"] = max(0, min(100, 100 - (expense_ratio - 30) * 1.5))  # 30% -> 100, 90% -> 0
    weights["expense_ratio"] = 0.20

    # Savings ratio: higher is better. >30% = 100, 0% = 0
    savings_ratio = cashflow.get("savings_ratio") or 0
    factors["savings_ratio"] = min(100, savings_ratio * 3.33)  # 30% -> 100
    weights["savings_ratio"] = 0.20

    # Free cash buffer: positive and reasonable = good
    free_cash = cashflow.get("free_cash") or 0
    total_income = cashflow.get("total_income") or 1
    buffer_pct = (free_cash / total_income * 100) if total_income else 0
    factors["free_cash_buffer"] = max(0, min(100, 50 + buffer_pct))  # 0% buffer -> 50, 50% buffer -> 100
    weights["free_cash_buffer"] = 0.15

    # Diversification score (from manager)
    div_score = manager.get("diversification_score") or 0
    factors["diversification"] = div_score
    weights["diversification"] = 0.15

    # Concentration: low concentration = good (inverse of max sector %)
    allocation = manager.get("allocation_by_sector") or {}
    max_sector = max(allocation.values()) if allocation else 100
    factors["concentration"] = max(0, 100 - max_sector)  # 100% one sector -> 0, spread -> 100
    weights["concentration"] = 0.15

    # Investment consistency: have some investments this month or recently
    total_invested = cashflow.get("total_invested") or 0
    portfolio_value = portfolio.get("total_current_value") or 0
    if total_income > 0 and total_invested >= 0:
        invest_ratio = cashflow.get("investment_ratio") or 0
        factors["investment_consistency"] = min(100, invest_ratio * 5) if invest_ratio else (50 if portfolio_value > 0 else 30)
    else:
        factors["investment_consistency"] = 50
    weights["investment_consistency"] = 0.15

    # Goal progress: if goals exist, average progress (optional; weight lower)
    try:
        import database
        goals = database.get_goals("active", user_id=user_id)
        if goals:
            progresses = []
            for g in goals:
                t = float(g.get("target_amount") or 1)
                c = float(g.get("current_amount") or 0)
                progresses.append(min(100, (c / t) * 100) if t else 0)
            factors["goal_progress"] = sum(progresses) / len(progresses) if progresses else 50
        else:
            factors["goal_progress"] = 50  # neutral
    except Exception:
        factors["goal_progress"] = 50
    weights["goal_progress"] = 0.05

    # Weighted score
    total_weight = sum(weights.values())
    score = sum(factors.get(k, 50) * weights.get(k, 0) for k in weights) / total_weight if total_weight else 50
    score = max(0, min(100, round(score, 0)))

    return {
        "score": int(score),
        "factors": {k: round(v, 1) for k, v in factors.items()},
        "weights": weights,
    }
