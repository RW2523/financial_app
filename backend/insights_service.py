"""
Advanced insights engine: deterministic metrics from expense history.
Optional LLM layer explains precomputed insights only.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import statistics

def _parse_date(d: str) -> Optional[datetime]:
    if not d:
        return None
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _filter_by_range(expenses: List[Dict], start_date: str, end_date: str) -> List[Dict]:
    """Return expenses with date in [start_date, end_date] (inclusive)."""
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if not start or not end:
        return []
    out = []
    for e in expenses:
        dt = _parse_date(e.get("date"))
        if dt and start <= dt <= end:
            out.append(e)
    return out


def _prev_period(start_date: str, end_date: str) -> tuple:
    """Return (prev_start, prev_end) for same-length period before start_date."""
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if not start or not end:
        return (None, None)
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return (prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d"))


def _total_spend(expenses: List[Dict]) -> float:
    return sum(float(e.get("amount") or 0) for e in expenses)


def compute_overview(
    expenses: List[Dict],
    start_date: str,
    end_date: str,
    previous_period_expenses: Optional[List[Dict]] = None,
    recurring_monthly_total: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute overview KPIs for the date range.
    If previous_period_expenses not provided, we do not compute deltas.
    recurring_monthly_total: optional sum of typical_amount from recurring (monthly) for burden.
    """
    period = _filter_by_range(expenses, start_date, end_date)
    total = _total_spend(period)
    count = len(period)
    avg_amount = total / count if count else 0

    # Category breakdown
    by_cat: Dict[str, float] = defaultdict(float)
    for e in period:
        cat = (e.get("category") or "other").strip().lower()
        by_cat[cat] += float(e.get("amount") or 0)
    category_breakdown = [{"category": k, "total": round(v, 2)} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])]

    # Top merchants by spend
    by_merchant: Dict[str, float] = defaultdict(float)
    for e in period:
        m = (e.get("merchant") or "").strip() or "(no merchant)"
        by_merchant[m] += float(e.get("amount") or 0)
    top_merchants = [{"merchant": k, "total": round(v, 2)} for k, v in sorted(by_merchant.items(), key=lambda x: -x[1])[:10]]

    # Spend delta vs previous period
    spend_delta = None
    spend_delta_percent = None
    if previous_period_expenses:
        prev_total = _total_spend(previous_period_expenses)
        if prev_total and prev_total != 0:
            spend_delta = round(total - prev_total, 2)
            spend_delta_percent = round((total - prev_total) / prev_total * 100, 1)

    # Biggest category increase (current period category total - previous period same category)
    biggest_category_increase = None
    if previous_period_expenses:
        prev_by_cat: Dict[str, float] = defaultdict(float)
        for e in previous_period_expenses:
            cat = (e.get("category") or "other").strip().lower()
            prev_by_cat[cat] += float(e.get("amount") or 0)
        increases = []
        for cat, curr in by_cat.items():
            prev = prev_by_cat.get(cat, 0)
            if prev == 0 and curr > 0:
                increases.append((cat, curr, float("inf")))
            elif prev > 0:
                pct = (curr - prev) / prev * 100
                increases.append((cat, curr - prev, pct))
        if increases:
            biggest = max(increases, key=lambda x: x[1])
            biggest_category_increase = {"category": biggest[0], "delta": round(biggest[1], 2), "delta_percent": round(biggest[2], 1)}

    # Weekday vs weekend
    weekday_total = 0.0
    weekend_total = 0.0
    for e in period:
        dt = _parse_date(e.get("date"))
        if dt:
            # 5=Saturday, 6=Sunday
            if dt.weekday() in (5, 6):
                weekend_total += float(e.get("amount") or 0)
            else:
                weekday_total += float(e.get("amount") or 0)
    weekday_vs_weekend = {"weekday_total": round(weekday_total, 2), "weekend_total": round(weekend_total, 2)}

    # Highest spending day
    by_day: Dict[str, float] = defaultdict(float)
    for e in period:
        d = str(e.get("date", ""))[:10]
        if d:
            by_day[d] += float(e.get("amount") or 0)
    highest_day = None
    if by_day:
        day, amt = max(by_day.items(), key=lambda x: x[1])
        highest_day = {"date": day, "total": round(amt, 2)}

    # Recurring burden: recurring_monthly_total as share of period spend (period may be > 1 month)
    recurring_burden = None
    if recurring_monthly_total is not None and total > 0:
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        if start and end:
            months_span = max(0.1, (end - start).days / 30.0)
            recurring_in_period = recurring_monthly_total * months_span
            recurring_burden = round(recurring_in_period / total * 100, 1)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_spend": round(total, 2),
        "transaction_count": count,
        "average_transaction_amount": round(avg_amount, 2),
        "category_breakdown": category_breakdown,
        "top_merchants": top_merchants,
        "spend_delta": spend_delta,
        "spend_delta_percent": spend_delta_percent,
        "biggest_category_increase": biggest_category_increase,
        "weekday_vs_weekend": weekday_vs_weekend,
        "highest_spending_day": highest_day,
        "recurring_burden_percent": recurring_burden,
    }


def compute_trends(expenses: List[Dict], months: int = 6) -> Dict[str, Any]:
    """Last N months: per-month total and category breakdown."""
    if months < 1:
        months = 1
    end = datetime.now()
    trends = []
    for i in range(months - 1, -1, -1):
        d = end - timedelta(days=30 * i)
        year, month = d.year, d.month
        start_str = f"{year}-{month:02d}-01"
        last_day = (datetime(year, month + 1, 1) - timedelta(days=1)).day if month < 12 else (datetime(year + 1, 1, 1) - timedelta(days=1)).day
        end_str = f"{year}-{month:02d}-{last_day}"
        period = _filter_by_range(expenses, start_str, end_str)
        total = _total_spend(period)
        by_cat: Dict[str, float] = defaultdict(float)
        for e in period:
            cat = (e.get("category") or "other").strip().lower()
            by_cat[cat] += float(e.get("amount") or 0)
        trends.append({
            "year": year,
            "month": month,
            "label": f"{year}-{month:02d}",
            "total_spend": round(total, 2),
            "transaction_count": len(period),
            "by_category": {k: round(v, 2) for k, v in by_cat.items()},
        })
    return {"months": months, "trends": trends}


def compute_categories(expenses: List[Dict], start_date: str, end_date: str) -> Dict[str, Any]:
    """Category breakdown for the date range."""
    period = _filter_by_range(expenses, start_date, end_date)
    by_cat: Dict[str, float] = defaultdict(float)
    for e in period:
        cat = (e.get("category") or "other").strip().lower()
        by_cat[cat] += float(e.get("amount") or 0)
    total = sum(by_cat.values())
    breakdown = [{"category": k, "total": round(v, 2), "percent": round(v / total * 100, 1) if total else 0} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])]
    return {"start_date": start_date, "end_date": end_date, "total": round(total, 2), "breakdown": breakdown}


def compute_anomalies(
    expenses: List[Dict],
    start_date: str,
    end_date: str,
    z_threshold: float = 2.0,
    top_percentile: float = 95.0,
) -> Dict[str, Any]:
    """
    Deterministic anomalies: z-score within category, merchant deviation, top percentile by amount.
    """
    period = _filter_by_range(expenses, start_date, end_date)
    if not period:
        return {"start_date": start_date, "end_date": end_date, "anomalies": [], "by_z_score": [], "top_percentile": []}

    # Z-score within category: (amount - category_mean) / category_std
    by_cat: Dict[str, List[float]] = defaultdict(list)
    for e in period:
        cat = (e.get("category") or "other").strip().lower()
        by_cat[cat].append(float(e.get("amount") or 0))
    by_z_score = []
    for e in period:
        cat = (e.get("category") or "other").strip().lower()
        amounts = by_cat.get(cat, [])
        amt = float(e.get("amount") or 0)
        if len(amounts) >= 2:
            mean = statistics.mean(amounts)
            stdev = statistics.stdev(amounts)
            if stdev > 0:
                z = (amt - mean) / stdev
                if abs(z) >= z_threshold:
                    by_z_score.append({
                        "expense_id": e.get("id"),
                        "date": e.get("date"),
                        "category": cat,
                        "amount": amt,
                        "merchant": e.get("merchant"),
                        "z_score": round(z, 2),
                        "reason": "high_z_score_within_category",
                    })
        elif len(amounts) == 1 and amt > 0:
            pass  # no variance

    # Merchant amount deviation: vs that merchant's mean in period
    by_merchant: Dict[str, List[float]] = defaultdict(list)
    for e in period:
        m = (e.get("merchant") or "").strip() or "(no merchant)"
        by_merchant[m].append(float(e.get("amount") or 0))
    merchant_deviation = []
    for e in period:
        m = (e.get("merchant") or "").strip() or "(no merchant)"
        amounts = by_merchant.get(m, [])
        amt = float(e.get("amount") or 0)
        if len(amounts) >= 2:
            mean = statistics.mean(amounts)
            stdev = statistics.stdev(amounts)
            if stdev > 0:
                z = (amt - mean) / stdev
                if abs(z) >= z_threshold:
                    merchant_deviation.append({
                        "expense_id": e.get("id"),
                        "date": e.get("date"),
                        "merchant": m,
                        "amount": amt,
                        "category": e.get("category"),
                        "z_score": round(z, 2),
                        "reason": "merchant_amount_deviation",
                    })

    # Top percentile by amount (unusual high expenses)
    all_amounts = sorted([float(e.get("amount") or 0) for e in period], reverse=True)
    top_percentile_list = []
    if all_amounts:
        # Index for percentile: 95th = top 5%, so threshold is value at position that leaves 5% above
        idx = max(0, int(len(all_amounts) * (100 - top_percentile) / 100))
        threshold = all_amounts[min(idx, len(all_amounts) - 1)] if all_amounts else 0
        for e in period:
            amt = float(e.get("amount") or 0)
            if amt >= threshold:
                top_percentile_list.append({
                    "expense_id": e.get("id"),
                    "date": e.get("date"),
                    "amount": amt,
                    "category": e.get("category"),
                    "merchant": e.get("merchant"),
                    "reason": "top_percentile",
                })
        top_percentile_list.sort(key=lambda x: -x["amount"])
        top_percentile_list = top_percentile_list[:20]

    # Dedupe and merge: prefer by_z_score and merchant_deviation, add top_percentile
    seen_ids = set()
    anomalies = []
    for a in by_z_score + merchant_deviation:
        eid = a.get("expense_id")
        if eid not in seen_ids:
            seen_ids.add(eid)
            anomalies.append(a)
    for a in top_percentile_list:
        eid = a.get("expense_id")
        if eid not in seen_ids:
            seen_ids.add(eid)
            anomalies.append(a)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "anomalies": anomalies,
        "z_threshold": z_threshold,
        "top_percentile": top_percentile,
    }


def get_recurring_monthly_total() -> Optional[float]:
    """Sum of typical_amount for monthly recurring expenses (for burden)."""
    try:
        import database
        rows = database.get_recurring_expenses()
        total = 0.0
        for r in rows:
            if (r.get("frequency_type") or "").lower() == "monthly":
                total += float(r.get("typical_amount") or 0)
        return total if total > 0 else None
    except Exception:
        return None


def generate_insights_narrative(structured_insights: Dict[str, Any]) -> str:
    """
    Optional LLM layer: explain precomputed insights using exact values.
    Prompt includes exact numbers; LLM does not invent data.
    """
    try:
        from llm_service import call_ollama
    except ImportError:
        return "LLM not available."
    import json
    prompt = """You are a financial insights assistant. Below are exact computed insights from the user's expense data. Summarize them in 2-4 short paragraphs. Use only the numbers provided; do not invent any data. Be concise and actionable.

Computed insights (JSON):
"""
    prompt += json.dumps(structured_insights, indent=2)
    prompt += "\n\nWrite a brief narrative summary using these numbers only:"
    try:
        return call_ollama(prompt, temperature=0.4)
    except Exception as e:
        return f"Narrative could not be generated: {str(e)}"
