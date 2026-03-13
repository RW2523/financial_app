"""
Financial scenario simulator. Read-only: no DB mutation.
Applies hypothetical adjustments to projected spending/limits and returns baseline vs simulated comparison.
"""
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Any, Optional

import database


def _monthly_equivalent(recurring_row: Dict) -> float:
    """Convert recurring row to monthly amount for projection."""
    freq = (recurring_row.get("frequency_type") or "").strip().lower()
    amount = float(recurring_row.get("typical_amount") or 0)
    if freq == "monthly":
        return amount
    if freq == "weekly":
        return round(amount * 4.33, 2)
    if freq == "biweekly":
        return round(amount * 2.15, 2)
    return amount  # treat other as monthly


def run_simulation(
    adjustments: List[Dict[str, Any]],
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run scenario simulation. Does not modify any database state.
    Returns baseline_summary, simulated_summary, delta_summary, projected_limit_changes, goal_impact.
    """
    now = datetime.now()
    y = year or now.year
    m = month or now.month

    # --- Baseline (read-only) ---
    import forecast_service as fs
    baseline_proj = fs.projected_month_end(y, m)
    baseline_by_cat = deepcopy(baseline_proj.get("by_category") or {})
    baseline_total = float(baseline_proj.get("projected_total") or 0)
    if "total" not in baseline_by_cat:
        baseline_by_cat["total"] = baseline_total

    limits_list = database.get_limits()
    baseline_limits = {r["category"]: float(r["amount"]) for r in limits_list}

    recurring_rows = database.get_recurring_expenses()
    goals = database.get_goals("active")

    # --- Simulated state (copies) ---
    sim_by_cat = deepcopy(baseline_by_cat)
    sim_total = baseline_total
    sim_limits = deepcopy(baseline_limits)

    # Track recurring we "removed" so we subtract correct category
    removed_recurring_monthly: Dict[str, float] = {}  # category -> amount removed

    # --- Apply adjustments in order ---
    for adj in adjustments:
        adj_type = (adj.get("type") or "").strip().lower()
        if adj_type == "reduce_category_percent":
            cat = (adj.get("category") or "").strip().lower() or "other"
            value = float(adj.get("value") or 0)
            if value < 0:
                value = 0
            if value > 100:
                value = 100
            pct = 1.0 - (value / 100.0)
            if cat not in sim_by_cat:
                sim_by_cat[cat] = 0.0
            old = sim_by_cat[cat]
            sim_by_cat[cat] = round(old * pct, 2)
            sim_total = round(sim_total - (old - sim_by_cat[cat]), 2)

        elif adj_type == "remove_recurring_merchant":
            merchant = (adj.get("merchant") or "").strip().lower()
            if not merchant:
                continue
            for r in recurring_rows:
                m_cur = (r.get("merchant") or "").strip().lower()
                if merchant in m_cur or m_cur in merchant:
                    cat = (r.get("category") or "other").strip().lower()
                    monthly = _monthly_equivalent(r)
                    if cat not in sim_by_cat:
                        sim_by_cat[cat] = 0.0
                    sim_by_cat[cat] = round(sim_by_cat[cat] - monthly, 2)
                    if sim_by_cat[cat] < 0:
                        sim_by_cat[cat] = 0.0
                    sim_total = round(sim_total - monthly, 2)
                    removed_recurring_monthly[cat] = removed_recurring_monthly.get(cat, 0) + monthly
                    break  # one match per adjustment

        elif adj_type == "add_one_time_expense":
            cat = (adj.get("category") or "other").strip().lower()
            amount = float(adj.get("amount") or 0)
            if cat not in sim_by_cat:
                sim_by_cat[cat] = 0.0
            sim_by_cat[cat] = round(sim_by_cat[cat] + amount, 2)
            sim_total = round(sim_total + amount, 2)

        elif adj_type == "change_category_cap":
            cat = (adj.get("category") or "").strip().lower()
            cap = float(adj.get("amount") or adj.get("value") or 0)
            if cap < 0:
                cap = 0
            sim_limits[cat] = cap

        elif adj_type == "save_fixed_per_week":
            value = float(adj.get("value") or adj.get("amount") or 0)
            if value < 0:
                value = 0
            monthly_savings = round(value * 4.33, 2)
            sim_total = round(sim_total - monthly_savings, 2)
            if sim_total < 0:
                sim_total = 0

    sim_by_cat["total"] = sim_total

    # --- Summaries ---
    baseline_summary = {
        "year": y,
        "month": m,
        "projected_total": round(baseline_total, 2),
        "by_category": {k: round(v, 2) for k, v in baseline_by_cat.items()},
        "limits": baseline_limits,
        "recurring_monthly_total": _recurring_monthly_total(recurring_rows),
    }
    simulated_summary = {
        "year": y,
        "month": m,
        "projected_total": round(sim_total, 2),
        "by_category": {k: round(v, 2) for k, v in sim_by_cat.items()},
        "limits": sim_limits,
    }
    delta_summary = {
        "total_change": round(sim_total - baseline_total, 2),
        "by_category": {
            k: round(sim_by_cat.get(k, 0) - baseline_by_cat.get(k, 0), 2)
            for k in set(sim_by_cat.keys()) | set(baseline_by_cat.keys())
            if k != "total"
        },
    }
    delta_summary["by_category"]["total"] = delta_summary["total_change"]

    # --- Projected limit changes (would we be under/over limit after simulation?) ---
    projected_limit_changes = _limit_changes(
        baseline_by_cat, baseline_limits,
        sim_by_cat, sim_limits,
    )

    # --- Goal impact (would simulated spend help/hurt goals?) ---
    goal_impact = _goal_impact(baseline_by_cat, sim_by_cat, goals)

    return {
        "baseline_summary": baseline_summary,
        "simulated_summary": simulated_summary,
        "delta_summary": delta_summary,
        "projected_limit_changes": projected_limit_changes,
        "goal_impact": goal_impact,
    }


def _recurring_monthly_total(rows: List[Dict]) -> float:
    total = 0.0
    for r in rows:
        if (r.get("frequency_type") or "").lower() == "monthly":
            total += float(r.get("typical_amount") or 0)
        elif (r.get("frequency_type") or "").lower() == "weekly":
            total += float(r.get("typical_amount") or 0) * 4.33
        elif (r.get("frequency_type") or "").lower() == "biweekly":
            total += float(r.get("typical_amount") or 0) * 2.15
    return round(total, 2)


def _limit_changes(
    baseline_by_cat: Dict[str, float],
    baseline_limits: Dict[str, float],
    sim_by_cat: Dict[str, float],
    sim_limits: Dict[str, float],
) -> List[Dict[str, Any]]:
    out = []
    all_cats = set(baseline_limits.keys()) | set(sim_limits.keys())
    for cat in all_cats:
        base_lim = baseline_limits.get(cat)
        sim_lim = sim_limits.get(cat)
        base_spend = baseline_by_cat.get(cat, 0.0)
        sim_spend = sim_by_cat.get(cat, 0.0)
        rec = {
            "category": cat,
            "baseline_spend": round(base_spend, 2),
            "simulated_spend": round(sim_spend, 2),
            "baseline_limit": base_lim,
            "simulated_limit": sim_lim,
        }
        if base_lim is not None:
            rec["baseline_over"] = round(max(0, base_spend - base_lim), 2)
        if sim_lim is not None:
            rec["simulated_over"] = round(max(0, sim_spend - sim_lim), 2)
        out.append(rec)
    total_lim = baseline_limits.get("total") or sim_limits.get("total")
    if total_lim is not None:
        out.append({
            "category": "total",
            "baseline_spend": round(baseline_by_cat.get("total", 0), 2),
            "simulated_spend": round(sim_by_cat.get("total", 0), 2),
            "baseline_limit": total_lim,
            "simulated_limit": sim_limits.get("total", total_lim),
            "baseline_over": round(max(0, baseline_by_cat.get("total", 0) - total_lim), 2),
            "simulated_over": round(max(0, sim_by_cat.get("total", 0) - (sim_limits.get("total") or total_lim)), 2),
        })
    return out


def _goal_impact(
    baseline_by_cat: Dict[str, float],
    sim_by_cat: Dict[str, float],
    goals: List[Dict],
) -> List[Dict[str, Any]]:
    out = []
    for g in goals:
        gtype = (g.get("goal_type") or "").strip().lower()
        gcat = (g.get("category") or "").strip().lower() if g.get("category") else None
        target = float(g.get("target_amount") or 0)
        current = float(g.get("current_amount") or 0)
        base_spend = baseline_by_cat.get(gcat or "total", 0.0) if gcat else baseline_by_cat.get("total", 0.0)
        sim_spend = sim_by_cat.get(gcat or "total", 0.0) if gcat else sim_by_cat.get("total", 0.0)
        impact = {
            "goal_id": g.get("id"),
            "goal_type": gtype,
            "description": g.get("description") or gtype,
            "category": gcat,
            "target": target,
            "current_amount": current,
            "baseline_projected_spend": round(base_spend, 2),
            "simulated_projected_spend": round(sim_spend, 2),
        }
        if gtype == "savings_target":
            impact["baseline_remaining"] = round(max(0, target - current), 2)
            impact["simulated_improvement"] = "Savings goal unchanged by spend simulation."
        elif gtype in ("category_cap", "spending_reduction"):
            impact["baseline_over"] = round(max(0, base_spend - target), 2)
            impact["simulated_over"] = round(max(0, sim_spend - target), 2)
            impact["improves"] = sim_spend < base_spend and sim_spend <= target
        out.append(impact)
    return out
