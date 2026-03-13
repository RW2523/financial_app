"""
Recurring expense detection: scan historical expenses, identify repeating patterns
by merchant/category, similar amount, and date spacing. Deterministic logic only.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import statistics

# Amount tolerance: two amounts match if within this fraction of the larger (e.g. 0.12 = 12%)
AMOUNT_TOLERANCE = 0.12
# Minimum number of matching transactions to consider recurring
MIN_OCCURRENCES_MONTHLY = 3
MIN_OCCURRENCES_WEEKLY = 4
MIN_OCCURRENCES_BIWEEKLY = 3
# Gap (days) bands for frequency inference
DAYS_WEEKLY = (5, 10)
DAYS_BIWEEKLY = (12, 18)
DAYS_MONTHLY = (25, 35)
# Minimum distinct "periods" to reduce false positives (e.g. 2 distinct months for monthly)
MIN_DISTINCT_MONTHS = 2
MIN_DISTINCT_WEEKS = 3


def _parse_date(d: str) -> Optional[datetime]:
    """Parse YYYY-MM-DD or YYYY-MM-DD HH:MM:SS to date."""
    if not d:
        return None
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _amount_matches(a: float, b: float, tolerance: float = AMOUNT_TOLERANCE) -> bool:
    """True if a and b are within tolerance (fraction of max)."""
    if a <= 0 and b <= 0:
        return True
    if a <= 0 or b <= 0:
        return False
    mx = max(a, b)
    mn = min(a, b)
    return (mx - mn) / mx <= tolerance


def _get_representative_amount(amounts: List[float]) -> float:
    """Typical amount for the group (median)."""
    if not amounts:
        return 0.0
    return round(statistics.median(amounts), 2)


def _infer_frequency(gaps_days: List[float]) -> Tuple[str, float]:
    """
    Infer frequency from list of gaps in days. Returns (frequency_type, confidence 0..1).
    frequency_type: 'weekly' | 'biweekly' | 'monthly' | 'irregular_recurring'
    """
    if len(gaps_days) < 2:
        return ("irregular_recurring", 0.3)
    median_gap = statistics.median(gaps_days)
    stdev = statistics.stdev(gaps_days) if len(gaps_days) >= 2 else 0
    consistency = max(0, 1 - (stdev / 15)) if median_gap > 0 else 0

    if DAYS_WEEKLY[0] <= median_gap <= DAYS_WEEKLY[1]:
        return ("weekly", min(1.0, 0.5 + consistency * 0.5))
    if DAYS_BIWEEKLY[0] <= median_gap <= DAYS_BIWEEKLY[1]:
        return ("biweekly", min(1.0, 0.5 + consistency * 0.5))
    if DAYS_MONTHLY[0] <= median_gap <= DAYS_MONTHLY[1]:
        return ("monthly", min(1.0, 0.5 + consistency * 0.5))
    return ("irregular_recurring", min(0.6, 0.3 + consistency * 0.3))


def _next_expected_date(last_date: datetime, frequency_type: str) -> Optional[str]:
    """Compute next expected date from last_seen and frequency."""
    if frequency_type == "weekly":
        next_d = last_date + timedelta(days=7)
    elif frequency_type == "biweekly":
        next_d = last_date + timedelta(days=14)
    elif frequency_type == "monthly":
        next_d = last_date + timedelta(days=30)
    else:
        return None
    return next_d.strftime("%Y-%m-%d")


def _reduce_false_positives(
    dates: List[datetime],
    frequency_type: str,
) -> bool:
    """True if we have enough distinct periods to consider this recurring (not one-off)."""
    if len(dates) < 2:
        return False
    if frequency_type == "monthly":
        months = {d.year * 12 + d.month for d in dates}
        return len(dates) >= MIN_OCCURRENCES_MONTHLY and len(months) >= MIN_DISTINCT_MONTHS
    if frequency_type in ("weekly", "biweekly"):
        weeks = {(d.year, d.isocalendar()[1]) for d in dates}
        return len(weeks) >= MIN_DISTINCT_WEEKS
    months = {d.year * 12 + d.month for d in dates}
    return len(dates) >= 3 and len(months) >= 2


def detect_recurring(expenses: List[Dict]) -> List[Dict]:
    """
    Scan expenses and return list of detected recurring patterns.
    Each item: merchant, category, subcategory, typical_amount, currency, frequency_type,
    confidence_score, last_seen_date, next_expected_date, expense_count.
    """
    raw = []
    for e in expenses:
        date_str = e.get("date")
        dt = _parse_date(date_str)
        if not dt:
            continue
        amount = float(e.get("amount") or 0)
        if amount <= 0:
            continue
        merchant = (e.get("merchant") or "").strip() or None
        category = (e.get("category") or "other").strip().lower()
        currency = (e.get("currency") or "USD").strip().upper()
        subcategory = (e.get("subcategory") or "").strip() or None
        raw.append({
            "date": date_str,
            "dt": dt,
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "subcategory": subcategory,
            "currency": currency,
        })

    by_merchant_cat: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for r in raw:
        m = (r["merchant"] or r["category"]).lower()
        by_merchant_cat[(m, r["category"])].append(r)

    results = []
    for (merchant_key, category), group in by_merchant_cat.items():
        group.sort(key=lambda x: x["dt"])
        amount_clusters: List[List[Dict]] = []
        for g in group:
            placed = False
            for cluster in amount_clusters:
                ref = cluster[0]["amount"]
                if _amount_matches(g["amount"], ref):
                    cluster.append(g)
                    placed = True
                    break
            if not placed:
                amount_clusters.append([g])
        for cluster in amount_clusters:
            if len(cluster) < MIN_OCCURRENCES_MONTHLY:
                continue
            dates = [c["dt"] for c in cluster]
            gaps = []
            for i in range(1, len(dates)):
                delta = (dates[i] - dates[i - 1]).days
                gaps.append(delta)
            frequency_type, conf = _infer_frequency(gaps)
            if frequency_type == "monthly" and len(cluster) < MIN_OCCURRENCES_MONTHLY:
                continue
            if frequency_type == "weekly" and len(cluster) < MIN_OCCURRENCES_WEEKLY:
                continue
            if frequency_type == "biweekly" and len(cluster) < MIN_OCCURRENCES_BIWEEKLY:
                continue
            if not _reduce_false_positives(dates, frequency_type):
                continue
            count_boost = min(0.2, (len(cluster) - MIN_OCCURRENCES_MONTHLY) * 0.05)
            confidence_score = round(min(1.0, conf + count_boost), 2)
            last_dt = max(dates)
            last_seen_date = last_dt.strftime("%Y-%m-%d")
            next_expected_date = _next_expected_date(last_dt, frequency_type)
            typical_amount = _get_representative_amount([c["amount"] for c in cluster])
            merchant_display = cluster[0].get("merchant") or merchant_key
            subcat = cluster[0].get("subcategory")
            currency = cluster[0].get("currency", "USD")
            results.append({
                "merchant": merchant_display if merchant_display != category else None,
                "category": category,
                "subcategory": subcat,
                "typical_amount": typical_amount,
                "currency": currency,
                "frequency_type": frequency_type,
                "confidence_score": confidence_score,
                "last_seen_date": last_seen_date,
                "next_expected_date": next_expected_date,
                "expense_count": len(cluster),
            })
    return results


def recompute_recurring() -> List[Dict]:
    """
    Load all expenses from DB, run detection, clear and repopulate recurring_expenses, return list.
    """
    import database
    database.init_database()
    expenses = database.get_all_expenses()
    detected = detect_recurring(expenses)
    database.clear_recurring_expenses()
    for d in detected:
        database.insert_recurring_expense(
            merchant=d.get("merchant"),
            category=d["category"],
            subcategory=d.get("subcategory"),
            typical_amount=d["typical_amount"],
            currency=d.get("currency", "USD"),
            frequency_type=d["frequency_type"],
            confidence_score=d.get("confidence_score"),
            last_seen_date=d.get("last_seen_date"),
            next_expected_date=d.get("next_expected_date"),
            expense_count=d["expense_count"],
            status="active",
        )
    return detected
