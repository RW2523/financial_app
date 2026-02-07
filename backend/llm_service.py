import json
import requests
from typing import Dict, Optional

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1"

EXTRACTION_PROMPT = """You are an expense extraction assistant. Extract structured data from the user's expense description.

Extract:
- date: in YYYY-MM-DD format (if not specified, use today's date)
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


def extract_expense_data(text: str) -> Dict:
    """Extract structured expense data from natural language"""
    prompt = EXTRACTION_PROMPT.format(text=text)
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

        return data

    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {str(e)}\nResponse: {response}")


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
