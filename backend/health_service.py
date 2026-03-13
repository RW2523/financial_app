"""
Budget health score and grounded recommendation engine.
All metrics are computed from actual data; recommendations cite triggering metrics.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics

import database

# Configurable weights for health score (sum = 1.0). Each metric normalized 0-1 (higher = better).
HEALTH_WEIGHTS = {
    "budget_adherence": 0.30,
    "overspending_frequency": 0.20,
    "category_volatility": 0.15,
    "recurring_burden": 0.15,
    "discretionary_ratio": 0.10,
    "anomaly_frequency": 0.10,
}

# Recommendation triggers
NEAR_LIMIT_THRESHOLD = 0.80   # 80% of limit
RECURRING_BURDEN_HIGH = 0.35  # recurring / total > 35%
MERCHANT_DOMINANCE = 0.50     # top merchant share of discretionary > 50%
TRANSPORT_RISE_MOM_PCT = 15  # transport up >15% vs last month


def _this_month() -> tuple:
    t = datetime.now()
    return (t.year, t.month)


def _metric_budget_adherence(year: int, month: int) -> float:
    """0-1: higher when spending is within limits."""
    limits = database.get_limits()
    if not limits:
        return 1.0
    spending = database.get_spending_by_category_for_month(year, month)
    scores = []
    for lim in limits:
        cat = lim["category"]
        cap = float(lim["amount"])
        if cap <= 0:
            continue
        spent = spending.get(cat, 0.0)
        if spent <= cap:
            scores.append(1.0)
        else:
            over = (spent - cap) / cap
            scores.append(max(0.0, 1.0 - over))
    return sum(scores) / len(scores) if scores else 1.0


def _metric_overspending_frequency(months_back: int = 6) -> float:
    """0-1: higher when fewer months had any overspend."""
    t = datetime.now()
    over_count = 0
    for i in range(1, months_back + 1):
        if t.month <= i:
            y, m = t.year - 1, t.month - i + 12
        else:
            y, m = t.year, t.month - i
        limits = database.get_limits()
        spending = database.get_spending_by_category_for_month(y, m)
        for lim in limits:
            if float(lim["amount"]) <= 0:
                continue
            if spending.get(lim["category"], 0) >= float(lim["amount"]):
                over_count += 1
                break
    return max(0.0, 1.0 - (over_count / months_back))


def _metric_category_volatility(months_back: int = 6) -> float:
    """0-1: higher when month-to-month total spend is stable (low coefficient of variation)."""
    totals = []
    t = datetime.now()
    for i in range(1, months_back + 1):
        if t.month <= i:
            y, m = t.year - 1, t.month - i + 12
        else:
            y, m = t.year, t.month - i
        by_cat = database.get_spending_by_category_for_month(y, m)
        totals.append(by_cat.get("total", 0.0))
    if len(totals) < 2 or sum(totals) == 0:
        return 1.0
    mean = statistics.mean(totals)
    std = statistics.stdev(totals)
    cv = std / mean if mean else 0
    return max(0.0, 1.0 - min(1.0, cv))


def _metric_recurring_burden(year: int, month: int) -> float:
    """0-1: higher when recurring burden is lower (recurring/total spend)."""
    try:
        from insights_service import get_recurring_monthly_total
        recurring = get_recurring_monthly_total()
    except Exception:
        return 1.0
    if recurring is None or recurring <= 0:
        return 1.0
    by_cat = database.get_spending_by_category_for_month(year, month)
    total = by_cat.get("total", 0.0)
    if total <= 0:
        return 1.0
    burden = recurring / total
    return max(0.0, 1.0 - min(1.0, burden / 0.5))  # 50% burden -> 0


def _metric_discretionary_ratio(year: int, month: int) -> float:
    """0-1: higher when discretionary (entertainment + shopping) share is moderate. Treat high ratio as lower health."""
    by_cat = database.get_spending_by_category_for_month(year, month)
    total = by_cat.get("total", 0.0)
    if total <= 0:
        return 1.0
    disc = by_cat.get("entertainment", 0) + by_cat.get("shopping", 0)
    ratio = disc / total
    return max(0.0, 1.0 - ratio)  # 0% discretionary -> 1, 100% -> 0


def _metric_anomaly_frequency(year: int, month: int) -> float:
    """0-1: higher when fewer anomalies in recent period."""
    try:
        import calendar
        from insights_service import compute_anomalies
        start_str = f"{year}-{month:02d}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_str = f"{year}-{month:02d}-{last_day}"
        expenses = database.get_expenses_by_date_range(start_str, end_str)
        result = compute_anomalies(expenses, start_str, end_str)
        anomalies = len(result.get("anomalies", []))
        count = len(expenses)
        if count <= 0:
            return 1.0
        ratio = anomalies / count
        return max(0.0, 1.0 - min(1.0, ratio * 10))
    except Exception:
        return 1.0


def compute_health_score(
    year: Optional[int] = None,
    month: Optional[int] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compute budget health score 0-100 and component metrics.
    Uses HEALTH_WEIGHTS unless weights provided (keys same as HEALTH_WEIGHTS).
    """
    y, m = year or _this_month()[0], month or _this_month()[1]
    w = weights or HEALTH_WEIGHTS
    metrics = {
        "budget_adherence": _metric_budget_adherence(y, m),
        "overspending_frequency": _metric_overspending_frequency(),
        "category_volatility": _metric_category_volatility(),
        "recurring_burden": _metric_recurring_burden(y, m),
        "discretionary_ratio": _metric_discretionary_ratio(y, m),
        "anomaly_frequency": _metric_anomaly_frequency(y, m),
    }
    score = 0.0
    for k, v in metrics.items():
        score += (w.get(k) or 0) * v
    score = round(min(100, max(0, score * 100)), 1)
    return {
        "year": y,
        "month": m,
        "score": score,
        "metrics": {k: round(v, 3) for k, v in metrics.items()},
        "weights": dict(w),
    }


def generate_recommendations(year: Optional[int] = None, month: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Recommendation cards grounded only in computed metrics.
    Each item: id, type, title, metric_cited, value, suggestion.
    """
    y, m = year or _this_month()[0], month or _this_month()[1]
    out = []
    limits = database.get_limits()
    spending = database.get_spending_by_category_for_month(y, m)
    total = spending.get("total", 0.0) or 1e-9

    # 1. Food budget nearly exceeded
    for lim in limits:
        if lim["category"] != "food":
            continue
        cap = float(lim["amount"])
        if cap <= 0:
            continue
        spent = spending.get("food", 0.0)
        pct = spent / cap
        if pct >= NEAR_LIMIT_THRESHOLD:
            out.append({
                "id": "food_budget_nearly_exceeded",
                "type": "budget_near_limit",
                "title": "Food budget nearly exceeded",
                "metric_cited": "food_spend_vs_limit",
                "value": round(pct * 100, 1),
                "suggestion": f"Food spending is at {pct*100:.0f}% of your limit (${spent:,.2f} / ${cap:,.2f}). Consider trimming discretionary food spend for the rest of the month.",
            })
        break

    # 2. Transport spending rising month-over-month
    t = datetime.now()
    if t.month > 1:
        prev_m, prev_y = t.month - 1, t.year
    else:
        prev_m, prev_y = 12, t.year - 1
    prev_spending = database.get_spending_by_category_for_month(prev_y, prev_m)
    this_transport = spending.get("transport", 0.0)
    prev_transport = prev_spending.get("transport", 0.0)
    if prev_transport > 0 and this_transport > prev_transport:
        rise_pct = (this_transport - prev_transport) / prev_transport * 100
        if rise_pct >= TRANSPORT_RISE_MOM_PCT:
            out.append({
                "id": "transport_rising_mom",
                "type": "category_trend",
                "title": "Transport spending rising month-over-month",
                "metric_cited": "transport_mom_change_pct",
                "value": round(rise_pct, 1),
                "suggestion": f"Transport spending is up {rise_pct:.0f}% vs last month (${this_transport:,.2f} vs ${prev_transport:,.2f}). Review recent trips or subscriptions.",
            })

    # 3. Recurring subscriptions total is high
    try:
        from insights_service import get_recurring_monthly_total
        recurring = get_recurring_monthly_total()
    except Exception:
        recurring = None
    if recurring and total > 0:
        burden = recurring / total
        if burden >= RECURRING_BURDEN_HIGH:
            out.append({
                "id": "recurring_subscriptions_high",
                "type": "recurring_burden",
                "title": "Recurring subscriptions total is high",
                "metric_cited": "recurring_burden_ratio",
                "value": round(burden * 100, 1),
                "suggestion": f"Recurring expenses are {burden*100:.0f}% of this month's spend (${recurring:,.2f}). Consider reviewing subscriptions you rarely use.",
            })

    # 4. One merchant dominates discretionary spending
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    expenses = database.get_expenses_by_date_range(
        f"{y}-{m:02d}-01",
        f"{y}-{m:02d}-{last_day:02d}",
    )
    disc_total = 0.0
    by_merchant: Dict[str, float] = {}
    for e in expenses:
        cat = (e.get("category") or "").strip().lower()
        if cat not in ("entertainment", "shopping"):
            continue
        amt = float(e.get("amount") or 0)
        disc_total += amt
        m_name = (e.get("merchant") or "").strip() or "(no merchant)"
        by_merchant[m_name] = by_merchant.get(m_name, 0) + amt
    if disc_total > 0 and by_merchant:
        top_merchant = max(by_merchant.items(), key=lambda x: x[1])
        share = top_merchant[1] / disc_total
        if share >= MERCHANT_DOMINANCE and top_merchant[0] != "(no merchant)":
            out.append({
                "id": "one_merchant_dominates_discretionary",
                "type": "merchant_concentration",
                "title": "One merchant dominates discretionary spending",
                "metric_cited": "top_merchant_share_of_discretionary",
                "value": round(share * 100, 1),
                "suggestion": f"{top_merchant[0]} is {share*100:.0f}% of your entertainment + shopping spend (${top_merchant[1]:,.2f}). Diversifying could help control impulse spending.",
            })

    return out


def recommendations_with_optional_llm(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Optionally rephrase suggestion using LLM; do not change metric_cited or value."""
    try:
        from llm_service import call_ollama
    except ImportError:
        return recommendations
    out = []
    for r in recommendations:
        try:
            prompt = f"Rephrase this one-sentence budget suggestion more naturally. Keep the same meaning and numbers. Do not add new advice.\nSuggestion: {r['suggestion']}\nRephrased:"
            rephrased = call_ollama(prompt, temperature=0.3)
            if rephrased and len(rephrased.strip()) > 10:
                r = {**r, "suggestion": rephrased.strip()}
        except Exception:
            pass
        out.append(r)
    return out
