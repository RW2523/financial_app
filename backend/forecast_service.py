"""
Forecasting and predictive overspending alerts.
Uses: pace extrapolation, optional historical average fallback.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import calendar

import database


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _today() -> datetime:
    return datetime.now()


def _days_elapsed_in_month(year: int, month: int) -> int:
    """Number of days elapsed in the given month (1-based). If future month, 0."""
    today = _today()
    if year > today.year or (year == today.year and month > today.month):
        return 0
    if year < today.year or (year == today.year and month < today.month):
        return days_in_month(year, month)  # full month in past
    return today.day


def _historical_month_totals(category: Optional[str], months_back: int = 6) -> List[float]:
    """Previous months' total spend for this category (or total)."""
    today = _today()
    out = []
    for i in range(1, months_back + 1):
        if today.month <= i:
            y = today.year - 1
            m = today.month - i + 12
        else:
            y = today.year
            m = today.month - i
        by_cat = database.get_spending_by_category_for_month(y, m)
        if category:
            out.append(by_cat.get(category, 0.0))
        else:
            out.append(by_cat.get("total", 0.0))
    return out


def projected_month_end(year: int, month: int) -> Dict[str, Any]:
    """
    Projected end-of-month total and by-category using pace extrapolation.
    Fallback: historical average when no spend yet or days_elapsed < 1.
    """
    days_total = days_in_month(year, month)
    days_elapsed = _days_elapsed_in_month(year, month)
    spending_so_far = database.get_spending_by_category_until_day(year, month, days_elapsed or 1)
    spending_full_month = database.get_spending_by_category_for_month(year, month)

    # Total projection
    total_so_far = spending_so_far.get("total", 0.0)
    if days_elapsed >= 1 and total_so_far > 0:
        pace = total_so_far / days_elapsed
        projected_total = pace * days_total
    else:
        hist = _historical_month_totals(None)
        projected_total = sum(hist) / len(hist) if hist else total_so_far

    # By category
    categories = set(spending_so_far.keys()) | set(spending_full_month.keys()) - {"total"}
    by_category = {}
    for cat in categories:
        so_far = spending_so_far.get(cat, 0.0)
        if days_elapsed >= 1 and so_far > 0:
            pace = so_far / days_elapsed
            by_category[cat] = round(pace * days_total, 2)
        else:
            hist = _historical_month_totals(cat)
            by_category[cat] = round(sum(hist) / len(hist), 2) if hist else round(so_far, 2)

    return {
        "year": year,
        "month": month,
        "days_in_month": days_total,
        "days_elapsed": days_elapsed,
        "spend_so_far_total": round(total_so_far, 2),
        "projected_total": round(projected_total, 2),
        "by_category": by_category,
        "method": "pace" if days_elapsed >= 1 and total_so_far > 0 else "historical_avg",
    }


def projected_categories(year: int, month: int) -> Dict[str, Any]:
    """Projected category spend for month end (same as projected_month_end by_category with metadata)."""
    pm = projected_month_end(year, month)
    return {
        "year": year,
        "month": month,
        "projected_total": pm["projected_total"],
        "by_category": pm["by_category"],
        "days_elapsed": pm["days_elapsed"],
        "days_in_month": pm["days_in_month"],
    }


def _estimated_over_limit(projected: float, limit: float) -> float:
    """Amount by which projected exceeds limit (0 if under)."""
    if limit <= 0:
        return 0.0
    return max(0.0, projected - limit)


def _days_until_overspend(spend_so_far: float, limit: float, days_elapsed: int, days_in_month: int) -> Optional[int]:
    """
    Approximate days from today until cumulative spend would cross limit (linear pace).
    Returns None if already over or pace is zero or limit not set.
    """
    if limit <= 0 or days_elapsed <= 0 or spend_so_far >= limit:
        return None
    pace = spend_so_far / days_elapsed
    if pace <= 0:
        return None
    remaining_to_limit = limit - spend_so_far
    days_to_cross = remaining_to_limit / pace
    days_left_in_month = days_in_month - days_elapsed
    if days_to_cross > days_left_in_month:
        return None  # won't cross this month
    return int(round(days_to_cross))


def predictive_alerts(year: int, month: int) -> Dict[str, Any]:
    """
    Predictive alerts: categories (or total) with limits that are projected to exceed by month end.
    Keeps existing 80% and 100% alerts; adds "projected to exceed by $X by month end" and optional "days until likely overspend".
    """
    limits = database.get_limits()
    spending = database.get_spending_by_category_for_month(year, month)
    spending_until = database.get_spending_by_category_until_day(year, month, _days_elapsed_in_month(year, month) or 1)
    proj = projected_month_end(year, month)
    days_elapsed = proj["days_elapsed"]
    days_total = proj["days_in_month"]

    alerts = []
    for lim in limits:
        cat = lim["category"]
        limit_amt = float(lim["amount"])
        if limit_amt <= 0:
            continue
        spent = spending.get(cat, 0.0)
        projected = proj["projected_total"] if cat == "total" else proj["by_category"].get(cat, spent)
        over = _estimated_over_limit(projected, limit_amt)
        if over <= 0:
            continue
        spend_so_far = spending_until.get(cat, 0.0)
        days_until = _days_until_overspend(spend_so_far, limit_amt, days_elapsed, days_total) if days_elapsed >= 1 else None
        message = f"At current pace, {cat} spending is projected to exceed the limit by ${over:,.2f} by month end."
        if days_until is not None:
            message += f" (About {days_until} days until overspend.)"
        alerts.append({
            "category": cat,
            "limit": limit_amt,
            "spent": spent,
            "projected": round(projected, 2),
            "over_amount": round(over, 2),
            "days_until_overspend": days_until,
            "message": message,
        })

    return {
        "year": year,
        "month": month,
        "alerts": alerts,
        "projected_total": proj["projected_total"],
    }
