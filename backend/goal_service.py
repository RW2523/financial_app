"""
Goal tracking: create, update progress, distance to goal, suggested reduction.
Goal types: savings_target, spending_reduction, category_cap.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

import database

GOAL_TYPES = {"savings_target", "spending_reduction", "category_cap"}


def create_goal(
    goal_type: str,
    target_amount: float,
    current_amount: float = 0,
    target_date: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a goal and return the new row."""
    if goal_type not in GOAL_TYPES:
        goal_type = "savings_target"
    gid = database.create_goal(
        goal_type=goal_type,
        target_amount=target_amount,
        current_amount=current_amount,
        target_date=target_date,
        category=category,
        description=description or "",
        status="active",
    )
    row = database.get_goal(gid)
    return _enrich_goal(row) if row else {"id": gid}


def get_goals(status: str = "active") -> List[Dict[str, Any]]:
    """List goals with distance and suggested reduction."""
    rows = database.get_goals(status=status)
    return [_enrich_goal(r) for r in rows]


def update_goal_progress(goal_id: int, current_amount: float) -> bool:
    """Update current_amount and updated_at."""
    return database.update_goal(goal_id, current_amount=current_amount)


def distance_to_goal(goal: Dict[str, Any], year: int = None, month: int = None) -> Dict[str, Any]:
    """
    For savings_target: distance = target - current (positive = still to save).
    For spending_reduction / category_cap: distance = current - target (positive = over cap).
    """
    gtype = (goal.get("goal_type") or "savings_target").strip().lower()
    target = float(goal.get("target_amount") or 0)
    current = float(goal.get("current_amount") or 0)
    if gtype == "savings_target":
        remaining = max(0, target - current)
        return {"remaining": round(remaining, 2), "current": current, "target": target, "met": current >= target}
    else:
        over = max(0, current - target)
        return {"over_amount": round(over, 2), "current": current, "target": target, "met": current <= target}


def suggested_reduction_per_month(goal: Dict[str, Any], year: int = None, month: int = None) -> Optional[float]:
    """For spending_reduction/category_cap: how much to reduce per month to meet target. For savings_target: how much to save per month."""
    y = year or datetime.now().year
    m = month or datetime.now().month
    gtype = (goal.get("goal_type") or "savings_target").strip().lower()
    target = float(goal.get("target_amount") or 0)
    current = float(goal.get("current_amount") or 0)
    target_date = goal.get("target_date")
    if not target_date:
        return None
    try:
        end = datetime.strptime(target_date[:10], "%Y-%m-%d")
        now = datetime(y, m, min(datetime.now().day, 28))
        months_left = max(0, (end.year - now.year) * 12 + (end.month - now.month))
        if months_left <= 0:
            return None
        if gtype == "savings_target":
            remaining = max(0, target - current)
            return round(remaining / months_left, 2)
        else:
            over = max(0, current - target)
            return round(over / months_left, 2) if over else 0
    except Exception:
        return None


def suggested_reduction_per_week(goal: Dict[str, Any], year: int = None, month: int = None) -> Optional[float]:
    """Same as per month but divided by ~4.33."""
    per_month = suggested_reduction_per_month(goal, year, month)
    if per_month is None:
        return None
    return round(per_month / 4.33, 2)


def _enrich_goal(row: Dict) -> Dict[str, Any]:
    """Add distance_to_goal and suggested_reduction to goal dict."""
    d = dict(row)
    d["distance"] = distance_to_goal(d)
    d["suggested_reduction_per_month"] = suggested_reduction_per_month(d)
    d["suggested_reduction_per_week"] = suggested_reduction_per_week(d)
    return d


def get_goal_enriched(goal_id: int) -> Optional[Dict[str, Any]]:
    """Return a single goal by id with distance and suggested reduction, or None."""
    row = database.get_goal(goal_id)
    return _enrich_goal(row) if row else None
