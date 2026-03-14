import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1"

EXTRACTION_PROMPT = """You are an expense extraction assistant. Extract structured data from the user's expense description.

Today's date is {today_iso}. Use this when the user says "today", "yesterday", or does not specify a date.

Extract:
- date: in YYYY-MM-DD format. If the user says "today" or no date, use {today_iso}. If "yesterday", use the day before. If they give a specific date (e.g. 03/11/2026 or March 11 2026), use that in YYYY-MM-DD.
- category: one of [food, transport, shopping, entertainment, utilities, healthcare, other]
- amount: numeric value only
- currency: ISO code (USD, EUR, INR, etc.) - default to USD if not mentioned

User input: {text}

Respond ONLY with valid JSON in this exact format:
{{"date": "YYYY-MM-DD", "category": "category_name", "amount": 123.45, "currency": "USD"}}

JSON response:"""

ANALYTICS_PROMPT = """You are a financial analytics assistant. Analyze the following monthly expenses and provide insights.

Monthly Data:
{expense_data}

Provide a summary including:
1. Total spending by category
2. Highest expense category
3. Total monthly spending
4. Any notable spending patterns or recommendations

Be concise and actionable."""


def call_ollama(prompt: str, temperature: float = 0.3) -> str:
    """Call Ollama API with streaming disabled"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "temperature": temperature
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def _fix_extracted_date(date_str: str) -> str:
    """If the LLM returned an old/wrong year, use today's date instead."""
    today = datetime.now().date()
    try:
        extracted = datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
        # If extracted date is before current year, treat as wrong and use today
        if extracted.year < today.year:
            return today.isoformat()
        # If extracted is more than 1 year in the future, use today
        if extracted.year > today.year + 1:
            return today.isoformat()
        return date_str.strip()[:10]
    except Exception:
        return today.isoformat()


def extract_expense_data(text: str) -> Dict:
    """Extract structured expense data from natural language"""
    today_iso = datetime.now().strftime("%Y-%m-%d")
    prompt = EXTRACTION_PROMPT.format(text=text, today_iso=today_iso)
    response = call_ollama(prompt, temperature=0.1)

    # Try to parse JSON from response
    try:
        # Find JSON object in response
        start = response.find("{")
        end = response.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON object found in response")

        json_str = response[start:end]
        data = json.loads(json_str)

        # Validate required fields
        required = ["date", "category", "amount", "currency"]
        if not all(k in data for k in required):
            raise ValueError("Missing required fields in extracted data")

        # Fix wrong date: LLM often returns past years (e.g. 2023) when it has no current date
        data["date"] = _fix_extracted_date(data["date"])

        return data

    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {str(e)}\nResponse: {response}")


DOCUMENT_EXTRACTION_PROMPT = """You are an expense extraction assistant. The user has provided a document (receipt, invoice, or list of expenses). Extract EVERY expense line or total from the text.

Today's date is {today_iso}. Use it when no date is given.

For each expense extract:
- date: YYYY-MM-DD (use document date or today if not found)
- category: one of [food, transport, shopping, entertainment, utilities, healthcare, other]
- amount: numeric value only
- currency: USD, EUR, INR, etc. (default USD)
- merchant: store/vendor name if visible (optional)

Document text:
---
{text}
---

Respond ONLY with a valid JSON array. Each element has: "date", "category", "amount", "currency", and optionally "merchant".
Example: [{{"date": "2025-02-06", "category": "food", "amount": 25.50, "currency": "USD", "merchant": "Starbucks"}}]
If there is only one total with no line items, return one object in an array.
JSON array:"""


def extract_expenses_from_document(text: str) -> List[Dict[str, Any]]:
    """Extract all expenses from a document/receipt text. Returns list of dicts with date, category, amount, currency, merchant."""
    if not (text or text.strip()):
        return []
    today_iso = datetime.now().strftime("%Y-%m-%d")
    prompt = DOCUMENT_EXTRACTION_PROMPT.format(text=text.strip()[:8000], today_iso=today_iso)
    response = call_ollama(prompt, temperature=0.1)
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start == -1 or end <= start:
            return []
        arr = json.loads(response[start:end])
        if not isinstance(arr, list):
            arr = [arr] if isinstance(arr, dict) else []
        out = []
        for item in arr:
            if not isinstance(item, dict):
                continue
            date_val = item.get("date") or today_iso
            if isinstance(date_val, str):
                date_val = _fix_extracted_date(date_val)
            else:
                date_val = today_iso
            cat = (item.get("category") or "other").strip().lower()
            if cat not in ("food", "transport", "shopping", "entertainment", "utilities", "healthcare", "other"):
                cat = "other"
            try:
                amount = float(item.get("amount") or 0)
            except (TypeError, ValueError):
                amount = 0
            if amount <= 0:
                continue
            currency = (item.get("currency") or "USD").strip().upper()[:3]
            merchant = item.get("merchant")
            if isinstance(merchant, str):
                merchant = merchant.strip() or None
            out.append({
                "date": date_val,
                "category": cat,
                "amount": amount,
                "currency": currency,
                "merchant": merchant,
            })
        return out
    except Exception:
        return []


def generate_monthly_summary(expenses: list) -> str:
    """Generate AI insights from monthly expenses"""
    if not expenses:
        return "No expenses found for this month."

    # Format expense data for LLM
    expense_summary = "\n".join([
        f"- {exp['date']}: {exp['category']} - {exp['currency']} {exp['amount']:.2f}"
        for exp in expenses
    ])

    prompt = ANALYTICS_PROMPT.format(expense_data=expense_summary)
    return call_ollama(prompt, temperature=0.5)
