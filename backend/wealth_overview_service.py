"""
Wealth Hub Overview: aggregated summary strip, priority alerts, next actions, goal preview, net worth preview.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import database

# Suggestion ID -> frontend route for "destination" link
SUGGESTION_DESTINATIONS: Dict[str, str] = {
    "expense_ratio_high": "/wealth/cashflow",
    "free_cash_negative": "/wealth/cashflow",
    "free_cash_low": "/wealth/cashflow",
    "concentration_high": "/wealth/manager",
    "savings_ratio_low": "/wealth/cashflow",
    "recurring_limiting_savings": "/wealth/cashflow",
}
DEFAULT_SUGGESTION_DESTINATION = "/wealth/suggestions"

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_ALERTS_TOP_N = 3
NEXT_ACTIONS_TOP_N = 6
GOALS_PREVIEW_TOP_N = 5
ROOM_TO_INVEST_THRESHOLD = 100
CONCENTRATION_ALERT_PCT = 50


def get_overview(user_id: str = None, year: int = None, month: int = None) -> Dict[str, Any]:
    """
    Returns: summary_strip, priority_alerts (top 3), next_actions, wealth_score, net_worth_preview, goals_preview.
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    uid = user_id

    cashflow, portfolio = _fetch_cashflow_and_portfolio(uid, y, m)
    summary_strip = _build_summary_strip(cashflow, portfolio)

    wealth_score_val, wealth_score_factors_val = _fetch_wealth_score(uid)
    net_worth_preview = _fetch_net_worth_preview(uid, y, m)
    summary_strip["wealth_score"] = wealth_score_val
    if net_worth_preview is not None:
        summary_strip["net_worth"] = net_worth_preview.get("net_worth")

    priority_alerts = _build_priority_alerts(cashflow, portfolio, y, m, uid)
    next_actions = _build_next_actions(cashflow, portfolio, y, m, uid)
    goals_preview, has_goals = _build_goals_preview(uid)

    return {
        "year": y,
        "month": m,
        "summary_strip": summary_strip,
        "priority_alerts": priority_alerts[:PRIORITY_ALERTS_TOP_N],
        "next_actions": next_actions[:NEXT_ACTIONS_TOP_N],
        "wealth_score": wealth_score_val,
        "wealth_score_factors": wealth_score_factors_val,
        "net_worth_preview": net_worth_preview,
        "goals_preview": goals_preview,
        "has_goals": has_goals,
    }


def _fetch_cashflow_and_portfolio(uid: str, y: int, m: int) -> tuple:
    """Return (cashflow_summary, portfolio_summary) with current prices for accurate portfolio value."""
    try:
        import wealth_cashflow_service as cf
        import wealth_portfolio_service as ps
        import wealth_stock_service as wss
        cashflow = cf.get_cashflow_summary(y, m, user_id=uid)
        transactions = database.list_investment_transactions(user_id=uid)
        tickers = list({(t.get("ticker") or "").strip().upper() for t in transactions if (t.get("ticker") or "").strip()})
        current_prices = wss.get_current_prices_for_tickers(tickers) if tickers else {}
        portfolio = ps.get_portfolio_summary(user_id=uid, current_prices=current_prices)
        return cashflow, portfolio
    except Exception:
        return {}, {}


def _build_summary_strip(cashflow: Dict, portfolio: Dict) -> Dict[str, Any]:
    strip = {
        "net_income_this_month": cashflow.get("total_income") or 0,
        "total_expenses_this_month": cashflow.get("total_expenses") or 0,
        "free_cash_this_month": cashflow.get("free_cash") or 0,
        "invested_this_month": cashflow.get("total_invested") or 0,
        "portfolio_value": portfolio.get("total_current_value") or 0,
    }
    strip["net_worth"] = None
    return strip


def _fetch_wealth_score(uid: str) -> tuple:
    """Return (score, factors)."""
    try:
        import wealth_score_service as ws
        data = ws.compute_wealth_score(uid)
        return data.get("score"), data.get("factors") or {}
    except Exception:
        return None, {}


def _fetch_net_worth_preview(uid: str, y: int, m: int) -> Optional[Dict[str, Any]]:
    try:
        import wealth_networth_service as nw
        return nw.get_net_worth(uid, y, m)
    except Exception:
        return None


def _build_priority_alerts(cashflow: Dict, portfolio: Dict, y: int, m: int, uid: str) -> List[Dict]:
    alerts = []
    try:
        import wealth_suggestions_service as sug
        sug_data = sug.get_suggestions(y, m, uid)
        suggestions = sug_data.get("suggestions") or []
        sorted_sug = sorted(
            suggestions,
            key=lambda s: (SEVERITY_ORDER.get(s.get("severity"), 2), -s.get("value", 0)),
        )
        for s in sorted_sug[:PRIORITY_ALERTS_TOP_N]:
            alerts.append({
                "id": s.get("id"),
                "title": s.get("title"),
                "message": s.get("message"),
                "severity": s.get("severity"),
                "destination": SUGGESTION_DESTINATIONS.get(s.get("id"), DEFAULT_SUGGESTION_DESTINATION),
            })
    except Exception:
        pass

    free_cash = cashflow.get("free_cash") or 0
    if free_cash > ROOM_TO_INVEST_THRESHOLD:
        alerts.insert(0, {
            "id": "room_to_invest",
            "title": "Room to invest",
            "message": f"You have {free_cash:.0f} free cash this month. Consider adding to your portfolio.",
            "severity": "low",
            "destination": "/wealth/portfolio",
        })
    return alerts[:PRIORITY_ALERTS_TOP_N]


def _build_next_actions(cashflow: Dict, portfolio: Dict, y: int, m: int, uid: str) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = []
    salary_summary = database.get_monthly_income_summary(y, m, user_id=uid)
    total_income = (salary_summary.get("net_income") or 0) + (salary_summary.get("bonus_total") or 0)
    if total_income == 0:
        actions.append({"action": "Add this month's salary", "destination": "/wealth/salary", "reason": "No income recorded for this month"})

    actions.append({"action": "Record latest investment transaction", "destination": "/wealth/investments", "reason": "Keep portfolio up to date"})

    holdings = portfolio.get("holdings") or []
    total_val = portfolio.get("total_current_value") or 0
    if holdings and total_val > 0:
        top = holdings[0]
        top_val = top.get("current_value") or top.get("total_invested") or 0
        pct = (top_val / total_val) * 100
        if pct > CONCENTRATION_ALERT_PCT:
            actions.append({"action": "Review portfolio concentration", "destination": "/wealth/manager", "reason": f"Largest holding is {pct:.0f}% of portfolio"})

    actions.append({"action": "Check projected monthly surplus", "destination": "/wealth/projections", "reason": "See where you're headed"})

    goals = database.get_goals("active", user_id=uid)
    if goals:
        actions.append({"action": "Update a goal", "destination": "/wealth/goals", "reason": f"You have {len(goals)} active goal(s)"})
    else:
        actions.append({"action": "Create a goal", "destination": "/wealth/goals", "reason": "Set a target to track progress"})

    return actions


def _build_goals_preview(uid: str) -> tuple:
    """Return (goals_preview list, has_goals bool)."""
    goals_list = database.get_goals("active", user_id=uid)
    preview = []
    for g in goals_list[:GOALS_PREVIEW_TOP_N]:
        target = float(g.get("target_amount") or 0)
        current = float(g.get("current_amount") or 0)
        pct = (current / target * 100) if target else 0
        preview.append({
            "id": g.get("id"),
            "description": g.get("description") or g.get("goal_type"),
            "current": current,
            "target": target,
            "progress_pct": round(pct, 1),
        })
    return preview, len(goals_list) > 0
