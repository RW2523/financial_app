"""
Hybrid expense extraction: deterministic (regex/rules) first, LLM fallback for missing/ambiguous.
Produces confidence score, merchant, and verification metadata.
"""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

from models import ExpenseExtractionResult, ExtractionEvidence

# ----- Currency symbols and codes -----
CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "Rs": "INR",
    "CAD": "CAD",
    "AUD": "AUD",
}
CURRENCY_PATTERN = re.compile(
    r"(\$|€|£|¥|₹|Rs\.?|USD|EUR|GBP|INR|CAD|AUD)\s*(\d+(?:\.\d+)?)|"
    r"(\d+(?:\.\d+)?)\s*(dollars?|bucks?|euros?|pounds?|rupees?|usd|eur|inr)\b",
    re.I,
)

# ----- Amount patterns -----
AMOUNT_PATTERN = re.compile(
    r"\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dollars?|bucks?|usd)?|"
    r"(?:like|about|around)\s+(\d+(?:\.\d+)?)|"
    r"(\d+(?:\.\d+)?)\s*(?:dollars?|bucks?|euros?|pounds?|rupees?)",
    re.I,
)

# ----- Relative date phrases -----
RELATIVE_DATES = [
    (r"\b(today)\b", 0),
    (r"\b(yesterday)\b", -1),
    (r"\b(last\s+night)\b", -1),
    (r"\b(this\s+morning)\b", 0),
    (r"\b(this\s+afternoon)\b", 0),
    (r"\b(this\s+evening)\b", 0),
    (r"\b(last\s+week)\b", -7),
    (r"\b(day\s+before\s+yesterday)\b", -2),
]

# ----- Merchant patterns -----
MERCHANT_PATTERNS = [
    re.compile(r"\bat\s+([A-Za-z0-9\s&'_\-]+?)(?:\s+on\s+|\s*[,.]|$)", re.I),
    re.compile(r"\bfrom\s+([A-Za-z0-9\s&'_\-]+?)(?:\s+on\s+|\s*[,.]|$)", re.I),
    re.compile(r"\bpaid\s+([A-Za-z0-9\s&'_\-]+?)(?:\s+for\s+|\s*[,.]|$)", re.I),
    re.compile(r"\bto\s+([A-Za-z0-9\s&'_\-]+?)(?:\s+for\s+|\s*[,.]|$)", re.I),
    re.compile(r"\b(?:at|@)\s*([A-Za-z0-9\s&'_\-]+?)(?:\s+(\d+)|$)", re.I),
]

# ----- Merchant -> category map (normalized name -> category) -----
MERCHANT_CATEGORY_MAP = {
    "starbucks": "food",
    "uber": "transport",
    "lyft": "transport",
    "amazon": "shopping",
    "walmart": "shopping",
    "target": "shopping",
    "netflix": "entertainment",
    "spotify": "entertainment",
    "doordash": "food",
    "ubereats": "food",
    "grubhub": "food",
    "shell": "transport",
    "exxon": "transport",
    "trader joe": "food",
    "whole foods": "food",
    "costco": "shopping",
    "walgreens": "healthcare",
    "cvs": "healthcare",
    "electric": "utilities",
    "gas company": "utilities",
    "water company": "utilities",
}

# ----- Category keyword heuristics (text snippet -> category) -----
CATEGORY_KEYWORDS = [
    (re.compile(r"\b(groceries|food|lunch|dinner|breakfast|coffee|restaurant|meal|eat)\b", re.I), "food"),
    (re.compile(r"\b(uber|taxi|gas|petrol|transport|mbta|train|bus)\b", re.I), "transport"),
    (re.compile(r"\b(shopping|buy|store|amazon|walmart)\b", re.I), "shopping"),
    (re.compile(r"\b(movie|concert|entertainment|netflix|spotify)\b", re.I), "entertainment"),
    (re.compile(r"\b(rent|electric|water|utilities|bill)\b", re.I), "utilities"),
    (re.compile(r"\b(doctor|pharmacy|healthcare|hospital|cvs|walgreens)\b", re.I), "healthcare"),
]

VALID_CATEGORIES = {"food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other"}


def normalize_merchant(raw: str) -> str:
    """Normalize merchant: lowercase, trim, strip punctuation; apply alias map."""
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip().strip(".,;:-").strip()
    s = re.sub(r"\s+", " ", s).lower()
    # Simple alias map (extend via config later)
    aliases = {"starbucks coffee": "starbucks", "uber eats": "ubereats"}
    return aliases.get(s, s) if s in aliases else s


def extract_amount_currency(text: str) -> Tuple[Optional[float], Optional[str], bool]:
    """Deterministic amount and currency. Returns (amount, currency, from_rules)."""
    # Try symbol + number or number + word
    for m in CURRENCY_PATTERN.finditer(text):
        g = m.groups()
        if g[0] and g[1]:  # symbol then number
            currency = CURRENCY_SYMBOLS.get(g[0]) or g[0][:3].upper() if len(g[0]) <= 3 else "USD"
            try:
                amt = float(g[1].replace(",", ""))
                return amt, currency, True
            except ValueError:
                pass
        if g[2] is not None and g[3]:
            try:
                amt = float(g[2].replace(",", ""))
                cur = {"dollars": "USD", "bucks": "USD", "usd": "USD", "euros": "EUR", "eur": "EUR",
                       "pounds": "GBP", "rupees": "INR", "inr": "INR"}.get(g[3].lower(), "USD")
                return amt, cur, True
            except ValueError:
                pass
    # Fallback: first number that looks like money
    for m in AMOUNT_PATTERN.finditer(text):
        for g in m.groups():
            if g is not None:
                try:
                    amt = float(g.replace(",", ""))
                    if 0 < amt < 1e7:
                        return amt, "USD", True
                except ValueError:
                    pass
    return None, None, False


def parse_relative_date(text: str, today: datetime) -> Optional[str]:
    """Parse relative date phrases; return YYYY-MM-DD or None."""
    t = text.lower().strip()
    for pattern, delta_days in RELATIVE_DATES:
        if re.search(pattern, t, re.I):
            d = today.date() + timedelta(days=delta_days)
            return d.isoformat()
    return None


def extract_merchant(text: str) -> Tuple[Optional[str], bool]:
    """Extract probable merchant from patterns. Returns (normalized_merchant, from_rules)."""
    for pat in MERCHANT_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(1).strip() if m.lastindex >= 1 else ""
            if len(raw) > 1 and len(raw) < 80:
                return normalize_merchant(raw), True
    return None, False


def infer_category_from_rules(text: str, merchant: Optional[str]) -> Optional[str]:
    """Infer category from in-code merchant map and keyword heuristics (no DB)."""
    if merchant:
        for key, cat in MERCHANT_CATEGORY_MAP.items():
            if key in merchant:
                return cat
    for pattern, category in CATEGORY_KEYWORDS:
        if pattern.search(text):
            return category
    return None


def lookup_category_from_merchant_memory(normalized_merchant: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Look up category/subcategory from learned merchant memory (DB).
    Returns (category, subcategory) or None. Used by extract_expense when merchant is present.
    """
    try:
        from merchant_service import lookup_merchant_mapping
        return lookup_merchant_mapping(normalized_merchant)
    except Exception:
        return None


def _llm_extract_missing(text: str, partial: Dict[str, Any], today_iso: str) -> Dict[str, Any]:
    """Call LLM only for missing or uncertain fields. Returns full dict with date, category, amount, currency."""
    import llm_service
    try:
        full = llm_service.extract_expense_data(text)
        # Override with rule-based when we had high confidence
        if partial.get("amount") is not None and full.get("amount") is not None:
            full["amount"] = partial["amount"]
        if partial.get("currency"):
            full["currency"] = partial["currency"]
        if partial.get("date"):
            full["date"] = partial["date"]
        if partial.get("merchant"):
            full["merchant"] = partial["merchant"]
        return full
    except Exception:
        # Build minimal from partial so we never fail to return something valid
        out = {
            "date": partial.get("date") or today_iso,
            "category": partial.get("category") or "other",
            "amount": partial.get("amount") or 0.0,
            "currency": partial.get("currency") or "USD",
            "merchant": partial.get("merchant"),
        }
        return out


def compute_confidence(
    amount_from_rules: bool,
    currency_from_rules: bool,
    date_from_rules: bool,
    category_from_rules: bool,
    merchant_from_rules: bool,
    has_amount: bool,
    has_date: bool,
) -> float:
    """Score 0..1: higher when more fields from rules and complete."""
    score = 0.0
    if has_amount:
        score += 0.35 if amount_from_rules else 0.15
    if currency_from_rules:
        score += 0.15
    elif has_amount:
        score += 0.05
    if has_date:
        score += 0.2 if date_from_rules else 0.08
    if category_from_rules:
        score += 0.2
    else:
        score += 0.05
    if merchant_from_rules:
        score += 0.1
    return min(1.0, round(score, 3))


def extract_expense(text: str, source_type: Optional[str] = None) -> ExpenseExtractionResult:
    """
    Hybrid extraction: rules first, LLM fallback for missing/ambiguous.
    Returns ExpenseExtractionResult with confidence and evidence.
    """
    today = datetime.now()
    today_iso = today.strftime("%Y-%m-%d")

    # 1) Deterministic
    amount, currency, amount_rules = extract_amount_currency(text)
    date_rel = parse_relative_date(text, today)
    date_from_rules = date_rel is not None
    merchant_raw, merchant_rules = extract_merchant(text)

    # 1b) Category: prefer merchant memory (learned), then in-code rules, then LLM
    category_from_memory, subcategory_from_memory = (None, None)
    if merchant_raw:
        mem = lookup_category_from_merchant_memory(merchant_raw)
        if mem:
            category_from_memory, subcategory_from_memory = mem[0], mem[1]
    category_rules = category_from_memory or infer_category_from_rules(text, merchant_raw)

    # 2) Decide if we need LLM (missing amount, category, or date)
    need_llm = amount is None or category_rules is None or (date_rel is None and not re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}", text))

    partial = {
        "date": date_rel or today_iso,
        "category": category_rules or "other",
        "amount": amount,
        "currency": currency or "USD",
        "merchant": merchant_raw,
        "subcategory": subcategory_from_memory,
    }

    currency_from_rules = amount_rules  # when amount came from pattern, currency did too (or default USD)

    if need_llm:
        full = _llm_extract_missing(text, partial, today_iso)
        from llm_service import _fix_extracted_date
        full["date"] = _fix_extracted_date(full.get("date", today_iso))
        if partial.get("merchant"):
            full["merchant"] = partial["merchant"]
        if category_from_memory is not None:
            full["category"] = category_from_memory
            if subcategory_from_memory is not None:
                full["subcategory"] = subcategory_from_memory
        elif partial.get("subcategory"):
            full["subcategory"] = partial["subcategory"]
        partial = full
        amount = partial.get("amount")
        currency = partial.get("currency") or "USD"
        amount_rules = False
        currency_from_rules = False
        date_from_rules = False
        category_rules = False

    if amount is None:
        amount = 0.0
    if not currency:
        currency = "USD"

    confidence = compute_confidence(
        amount_from_rules=amount_rules,
        currency_from_rules=currency_from_rules,
        date_from_rules=date_from_rules,
        category_from_rules=category_rules is not None,
        merchant_from_rules=merchant_rules,
        has_amount=amount is not None and amount > 0,
        has_date=bool(partial.get("date")),
    )

    evidence = ExtractionEvidence(
        amount_source="rules" if amount_rules else "llm",
        currency_source="rules" if (currency_from_rules or amount_rules) else "llm",
        date_source="rules" if date_from_rules else "llm",
        category_source="rules" if category_rules else "llm",
        merchant_source="rules" if merchant_rules else "llm",
    )

    extracted_json = {
        "date": partial.get("date"),
        "category": partial.get("category"),
        "amount": amount,
        "currency": currency,
        "merchant": partial.get("merchant"),
        "subcategory": partial.get("subcategory"),
        "confidence_score": confidence,
        "evidence": evidence.model_dump(),
    }

    return ExpenseExtractionResult(
        date=partial.get("date", today_iso),
        category=partial.get("category", "other") or "other",
        amount=float(amount),
        currency=currency,
        merchant=partial.get("merchant") or merchant_raw,
        subcategory=partial.get("subcategory"),
        raw_text=text,
        confidence_score=confidence,
        evidence=evidence,
        extracted_json=extracted_json,
    )
