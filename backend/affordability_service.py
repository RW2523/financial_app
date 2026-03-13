"""
Affordability check: can I afford this purchase?
Considers: category limit, total limit, projected month-end spend, recurring obligations, active goals, spending pace.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

import database


def check_affordability(
    amount: float,
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    year: int = None,
    month: int = None,
) -> Dict[str, Any]:
    """
    Evaluate whether the user can afford this purchase.
    Returns can_afford, reasons[], projected_impact, budget_impact, goal_impact, recommendation_text.
    """
    y = year or datetime.now().year
    m = month or datetime.now().month
    reasons = []
    projected_impact = {}
    budget_impact = {}
    goal_impact = {}

    # Current spending and limits
    spending = database.get_spending_by_category_for_month(y, m)
    limits_list = database.get_limits()
    limits = {lim["category"]: float(lim["amount"]) for lim in limits_list if float(lim["amount"]) > 0}

    # Projected month-end (forecast)
    try:
        import forecast_service as fs
        proj = fs.projected_month_end(y, m)
        projected_total = proj["projected_total"]
        projected_by_cat = proj.get("by_category") or {}
    except Exception:
        projected_total = spending.get("total", 0)
        projected_by_cat = {k: v for k, v in spending.items() if k != "total"}

    # Recurring this month
    try:
        from insights_service import get_recurring_monthly_total
        recurring = get_recurring_monthly_total() or 0
    except Exception:
        recurring = 0

    # Category for this purchase (use provided or default)
    cat = (category or "other").strip().lower() if category else "other"
    current_cat_spend = spending.get(cat, 0.0)
    current_total = spending.get("total", 0.0)
    projected_cat = projected_by_cat.get(cat, current_cat_spend)
    # After adding this purchase: new cat spend = current_cat_spend + amount, new total = current_total + amount
    new_cat = current_cat_spend + amount
    new_total = current_total + amount

    # Budget impact
    cat_limit = limits.get(cat)
    total_limit = limits.get("total")
    over_cat = (new_cat - cat_limit) if cat_limit and cat_limit > 0 else 0
    over_total = (new_total - total_limit) if total_limit and total_limit > 0 else 0
    if cat_limit is not None:
        budget_impact["category_limit"] = cat_limit
        budget_impact["category_after"] = round(new_cat, 2)
        budget_impact["category_over"] = round(max(0, over_cat), 2)
    if total_limit is not None:
        budget_impact["total_limit"] = total_limit
        budget_impact["total_after"] = round(new_total, 2)
        budget_impact["total_over"] = round(max(0, over_total), 2)

    # Projected impact (would this push projected over?)
    projected_impact["current_total"] = round(current_total, 2)
    projected_impact["projected_month_end"] = round(projected_total, 2)
    projected_impact["after_purchase_total"] = round(new_total, 2)

    # Reasons
    if amount <= 0:
        reasons.append("Amount is zero or negative.")
        return _build_response(True, reasons, projected_impact, budget_impact, goal_impact, amount, cat_limit, total_limit, over_cat, over_total)

    if cat_limit is not None and new_cat > cat_limit:
        reasons.append(f"After this purchase, {cat} spending (${new_cat:,.2f}) would exceed the category limit (${cat_limit:,.2f}).")
    elif cat_limit is not None and new_cat <= cat_limit:
        reasons.append(f"Within {cat} limit (${new_cat:,.2f} / ${cat_limit:,.2f}).")

    if total_limit is not None and new_total > total_limit:
        reasons.append(f"After this purchase, total spending (${new_total:,.2f}) would exceed the total limit (${total_limit:,.2f}).")
    elif total_limit is not None and new_total <= total_limit:
        reasons.append(f"Within total limit (${new_total:,.2f} / ${total_limit:,.2f}).")

    # Goals: would this conflict with a category_cap or spending_reduction for this category?
    goals = database.get_goals("active")
    for g in goals:
        gtype = (g.get("goal_type") or "").strip().lower()
        gcat = (g.get("category") or "").strip().lower() if g.get("category") else None
        if gcat and gcat != cat:
            continue
        target = float(g.get("target_amount") or 0)
        current = float(g.get("current_amount") or 0)
        if gtype == "category_cap" and gcat == cat:
            if new_cat > target:
                reasons.append(f"Would exceed goal '{g.get('description') or gtype}' target (${target:,.2f}) for {cat}.")
                goal_impact["conflict"] = goal_impact.get("conflict", []) + [{"goal_id": g.get("id"), "target": target, "after": new_cat}]
        if gtype == "spending_reduction" and gcat == cat and target < current + amount:
            reasons.append(f"Purchase would slow progress on spending reduction goal.")
            goal_impact["conflict"] = goal_impact.get("conflict", []) + [{"goal_id": g.get("id")}]
    if not goal_impact:
        goal_impact["active_goals_checked"] = len(goals)

    # Recurring: mention if recurring is high
    if recurring > 0 and total_limit and (new_total + recurring) > total_limit:
        reasons.append(f"Recurring obligations this month (${recurring:,.2f}) plus this purchase would push total over limit.")

    can_afford = over_cat <= 0 and over_total <= 0 and not goal_impact.get("conflict")
    recommendation_text = _recommendation_text(can_afford, amount, cat, cat_limit, total_limit, over_cat, over_total, reasons)
    return {
        "can_afford": can_afford,
        "reasons": reasons,
        "projected_impact": projected_impact,
        "budget_impact": budget_impact,
        "goal_impact": goal_impact if goal_impact else None,
        "recommendation_text": recommendation_text,
    }


def _build_response(can_afford, reasons, projected_impact, budget_impact, goal_impact, amount, cat_limit, total_limit, over_cat, over_total):
    rec = _recommendation_text(can_afford, amount, "category", cat_limit, total_limit, over_cat, over_total, reasons)
    return {
        "can_afford": can_afford,
        "reasons": reasons,
        "projected_impact": projected_impact,
        "budget_impact": budget_impact or None,
        "goal_impact": goal_impact or None,
        "recommendation_text": rec,
    }


def _recommendation_text(
    can_afford: bool,
    amount: float,
    category: str,
    cat_limit: Optional[float],
    total_limit: Optional[float],
    over_cat: float,
    over_total: float,
    reasons: List[str],
) -> str:
    if can_afford:
        return f"This purchase (${amount:,.2f}) fits within your current limits. " + (f"({category}: under limit; total under limit.)" if (cat_limit or total_limit) else "")
    parts = []
    if over_cat > 0:
        parts.append(f"Would exceed {category} limit by ${over_cat:,.2f}.")
    if over_total > 0:
        parts.append(f"Would exceed total limit by ${over_total:,.2f}.")
    if not parts:
        parts.append("Consider your goals and spending pace.")
    return " ".join(parts)
