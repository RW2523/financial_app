"""
Safe natural language query over expense data.
Pipeline: question -> parse to structured schema -> validate -> safe DB query -> answer + rows.
No raw SQL from LLM; only structured filters.
"""
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Any

ALLOWED_INTENTS = {"sum", "list", "compare", "top_category", "top_month", "merchant_total", "category_total"}
ALLOWED_CATEGORIES = {"food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other"}

# Keywords that suggest out-of-scope (financial advice, prediction, etc.)
OUT_OF_SCOPE_PATTERNS = [
    r"\b(should i|can i|is it (a )?good (idea )?to|would you recommend|advise|invest|investment|stock|savings (tip|advice)|how (can i|do i) (save|invest)|best (way|strategy) to)\b",
    r"\b(predict|forecast|will i|what (will|might) happen)\b",
    r"\b(what will .* (be|be like)|expenses? (be|next year|next month))\b",
    r"\b(loan|credit (card )?debt|mortgage|refinanc)\b",
]

# Rule-based: relative date patterns
RELATIVE_DATE = {
    "last month": "last_month",
    "past month": "last_month",
    "this month": "this_month",
    "last year": "last_year",
    "this year": "this_year",
}

# Category hints from keywords (question -> category)
CATEGORY_HINTS = [
    (r"\bcoffee\b", "food"),
    (r"\bgrocer(y|ies)\b", "shopping"),
    (r"\b(gas|fuel|uber|lyft|taxi)\b", "transport"),
    (r"\b(netflix|spotify|subscription)\b", "entertainment"),
    (r"\b(amazon|walmart)\b", None),  # merchant, not category
]

# Merchant hints (substring in question -> merchant filter)
MERCHANT_HINTS = ["uber", "lyft", "amazon", "starbucks", "netflix", "walmart", "target", "doordash"]


def _parse_date(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _resolve_date_range(relative: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return (start_date, end_date) YYYY-MM-DD. Prefer explicit start/end; else resolve relative."""
    if start_date and end_date:
        return (start_date[:10], end_date[:10])
    now = datetime.now()
    if relative == "last_month":
        first = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last = now.replace(day=1) - timedelta(days=1)
        return (first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d"))
    if relative == "this_month":
        first = now.replace(day=1)
        return (first.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))
    if relative == "last_year":
        return (f"{now.year - 1}-01-01", f"{now.year - 1}-12-31")
    if relative == "this_year":
        return (f"{now.year}-01-01", now.strftime("%Y-%m-%d"))
    return (start_date[:10] if start_date else None, end_date[:10] if end_date else None)


def is_out_of_scope(question: str) -> bool:
    """True if question asks for financial advice, prediction, or other non-data answers."""
    if not question or len(question.strip()) < 5:
        return False
    q = question.lower().strip()
    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, q, re.I):
            return True
    return False


def parse_question_rules(question: str) -> Optional[Dict[str, Any]]:
    """Rule-based extraction. Returns dict suitable for ParsedQuerySchema or None."""
    if not question or len(question.strip()) < 3:
        return None
    q = question.lower().strip()
    out = {
        "intent": "sum",
        "start_date": None,
        "end_date": None,
        "category": None,
        "subcategory": None,
        "merchant": None,
        "min_amount": None,
        "max_amount": None,
        "limit": 50,
        "sort": "date_desc",
        "date_relative": None,
    }
    # Relative date
    for phrase, rel in RELATIVE_DATE.items():
        if phrase in q:
            out["date_relative"] = rel
            break
    # Year: e.g. "in 2025"
    year_m = re.search(r"\b(20\d{2})\b", q)
    if year_m:
        y = int(year_m.group(1))
        out["start_date"] = f"{y}-01-01"
        out["end_date"] = f"{y}-12-31"
        if out["date_relative"]:
            out["date_relative"] = None  # explicit year wins
    # Amount filters
    over_m = re.search(r"(?:over|above|more than)\s*\$?\s*([\d.]+)", q, re.I)
    if over_m:
        out["min_amount"] = float(over_m.group(1))
    under_m = re.search(r"(?:under|below|less than)\s*\$?\s*([\d.]+)", q, re.I)
    if under_m:
        out["max_amount"] = float(under_m.group(1))
    # Merchant
    for m in MERCHANT_HINTS:
        if m in q:
            out["merchant"] = m
            break
    # Category from hints
    for pattern, cat in CATEGORY_HINTS:
        if cat and re.search(pattern, q):
            out["category"] = cat
            break
    # Intent from phrasing
    if re.search(r"\b(show|list|give me|what are)\s+(my\s+)?(expenses?|transactions?)\b", q):
        out["intent"] = "list"
        out["sort"] = "date_desc"
    if re.search(r"\bhow much\s+(did i\s+)?(spend|pay)\b", q) and not re.search(r"\bwhich month\b", q):
        out["intent"] = "sum"
    if re.search(r"\bwhich month\s+(had|was)\s+(the\s+)?(highest|most)\b", q) or re.search(r"\bhighest\s+(grocery|spend|category)\b", q):
        out["intent"] = "top_month"
    if re.search(r"\b(top|highest)\s+category\b", q):
        out["intent"] = "top_category"
    if re.search(r"\b(uber|amazon|starbucks|merchant)\s+(expenses?|spend)\b", q) or (out["merchant"] and "total" in q):
        out["intent"] = "merchant_total"
    if re.search(r"\b(category|grocery|food)\s+total\b", q) or (out["category"] and "how much" in q):
        out["intent"] = "category_total" if out["intent"] == "sum" else out["intent"]
    return out


def parse_question_llm(question: str) -> Optional[Dict[str, Any]]:
    """Use LLM to extract ONLY structured schema (JSON). Never SQL."""
    try:
        from llm_service import call_ollama
    except ImportError:
        return None
    prompt = """You are a query parser for an expense tracker. Extract a structured query from the user's question.

Allowed intents: sum, list, top_category, top_month, merchant_total, category_total
Allowed categories: food, transport, shopping, entertainment, utilities, healthcare, other
Date: use "last_month", "this_month", "this_year", "last_year" or specific YYYY-MM-DD for start_date/end_date.
Merchant: any merchant name the user mentions (e.g. Uber, Amazon, Starbucks).
Amount: min_amount (over/above X), max_amount (under/below X).

User question: """
    prompt += question.strip() + "\n\nRespond ONLY with valid JSON in this exact format (use null for missing):\n"
    prompt += '{"intent": "sum", "start_date": null, "end_date": null, "category": null, "merchant": null, "min_amount": null, "max_amount": null, "date_relative": "last_month"}\nJSON:'
    try:
        resp = call_ollama(prompt, temperature=0.1)
        start = resp.find("{")
        end = resp.rfind("}") + 1
        if start == -1 or end <= start:
            return None
        data = json.loads(resp[start:end])
        out = {
            "intent": (data.get("intent") or "sum").lower(),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "category": data.get("category"),
            "subcategory": data.get("subcategory"),
            "merchant": data.get("merchant"),
            "min_amount": data.get("min_amount"),
            "max_amount": data.get("max_amount"),
            "limit": 50,
            "sort": "date_desc",
            "date_relative": data.get("date_relative"),
        }
        if out["intent"] not in ALLOWED_INTENTS:
            out["intent"] = "sum"
        return out
    except Exception:
        return None


def validate_and_resolve(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Validate intent/category and resolve date range."""
    intent = (parsed.get("intent") or "sum").lower()
    if intent not in ALLOWED_INTENTS:
        intent = "sum"
    category = parsed.get("category")
    if category:
        category = category.strip().lower()
        if category not in ALLOWED_CATEGORIES:
            category = None
    start, end = _resolve_date_range(
        parsed.get("date_relative"),
        parsed.get("start_date"),
        parsed.get("end_date"),
    )
    return {
        "intent": intent,
        "start_date": start,
        "end_date": end,
        "category": category,
        "subcategory": parsed.get("subcategory"),
        "merchant": parsed.get("merchant").strip() if parsed.get("merchant") else None,
        "min_amount": parsed.get("min_amount"),
        "max_amount": parsed.get("max_amount"),
        "limit": max(1, min(500, int(parsed.get("limit") or 50))),
        "sort": parsed.get("sort") or "date_desc",
    }


def execute_query(parsed: Dict[str, Any]) -> Tuple[List[Dict], Dict[str, Any]]:
    """Run safe DB query and compute aggregates. Returns (rows, aggregates)."""
    import database
    order_map = {"date_desc": "date DESC", "date_asc": "date ASC", "amount_desc": "amount DESC", "amount_asc": "amount ASC"}
    order = order_map.get(parsed.get("sort") or "date_desc", "date DESC")
    rows = database.query_expenses_safe(
        start_date=parsed.get("start_date"),
        end_date=parsed.get("end_date"),
        category=parsed.get("category"),
        merchant_like=parsed.get("merchant"),
        min_amount=parsed.get("min_amount"),
        max_amount=parsed.get("max_amount"),
        limit=parsed.get("limit", 50),
        order_by=order,
    )
    aggregates = {}
    intent = parsed.get("intent", "sum")
    if rows:
        total = sum(float(r.get("amount") or 0) for r in rows)
        aggregates["total"] = round(total, 2)
        aggregates["count"] = len(rows)
        if intent == "top_month":
            by_month: Dict[str, float] = defaultdict(float)
            for r in rows:
                d = str(r.get("date", ""))[:7]
                if d:
                    by_month[d] += float(r.get("amount") or 0)
            if by_month:
                top = max(by_month.items(), key=lambda x: x[1])
                aggregates["top_month"] = top[0]
                aggregates["top_month_total"] = round(top[1], 2)
        if intent == "top_category":
            by_cat: Dict[str, float] = defaultdict(float)
            for r in rows:
                c = (r.get("category") or "other").lower()
                by_cat[c] += float(r.get("amount") or 0)
            if by_cat:
                top = max(by_cat.items(), key=lambda x: x[1])
                aggregates["top_category"] = top[0]
                aggregates["top_category_total"] = round(top[1], 2)
    return (rows, aggregates)


def format_answer(parsed: Dict[str, Any], rows: List[Dict], aggregates: Dict[str, Any]) -> str:
    """Build answer_text from parsed query and results."""
    intent = parsed.get("intent", "sum")
    if not rows:
        return "I didn't find any expenses matching that."
    total = aggregates.get("total", 0)
    count = aggregates.get("count", 0)
    if intent == "sum" or intent == "category_total" or intent == "merchant_total":
        return f"You spent **${total:,.2f}** across **{count}** matching transaction(s)."
    if intent == "list":
        return f"Found **{count}** matching transaction(s). Total: **${total:,.2f}**."
    if intent == "top_month":
        m = aggregates.get("top_month", "")
        t = aggregates.get("top_month_total", 0)
        return f"The month with the highest matching spend was **{m}** with **${t:,.2f}**."
    if intent == "top_category":
        c = aggregates.get("top_category", "")
        t = aggregates.get("top_category_total", 0)
        return f"The top category was **{c}** with **${t:,.2f}**."
    return f"Found **{count}** transaction(s). Total: **${total:,.2f}**."


def answer_question(question: str) -> Dict[str, Any]:
    """
    Full pipeline: parse -> validate -> query -> format.
    Returns dict with question, parsed_query, answer_text, rows, aggregates, refused.
    """
    if is_out_of_scope(question):
        return {
            "question": question,
            "parsed_query": {},
            "answer_text": "I can only answer questions about your recorded expense history (totals, categories, merchants, time ranges). I can't give financial advice, predictions, or recommendations.",
            "rows": [],
            "aggregates": None,
            "refused": True,
        }
    parsed = parse_question_rules(question)
    if not parsed:
        parsed = parse_question_llm(question)
    if not parsed:
        parsed = {"intent": "sum", "start_date": None, "end_date": None, "limit": 50, "sort": "date_desc"}
    parsed = validate_and_resolve(parsed)
    rows, aggregates = execute_query(parsed)
    answer_text = format_answer(parsed, rows, aggregates)
    # Schema for API (no date_relative in response)
    schema_out = {
        "intent": parsed["intent"],
        "start_date": parsed["start_date"],
        "end_date": parsed["end_date"],
        "category": parsed["category"],
        "merchant": parsed["merchant"],
        "min_amount": parsed["min_amount"],
        "max_amount": parsed["max_amount"],
        "limit": parsed["limit"],
        "sort": parsed["sort"],
    }
    return {
        "question": question,
        "parsed_query": schema_out,
        "answer_text": answer_text,
        "rows": rows,
        "aggregates": aggregates or None,
        "refused": False,
    }
