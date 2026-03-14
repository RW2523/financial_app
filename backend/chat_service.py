"""
Unified chat: add expenses, run app actions (limits, goals, affordability, etc.), or answer questions.
Intent order: action (help, set limit, goals, …) -> question -> add expense -> fallback ask.
"""
import re
import json
import database
import extraction_service
from config import is_auto_verified

# Phrases that suggest a question (NL query) rather than logging an expense
QUESTION_STARTS = (
    r"^(how much|what|when|which|show me|list|give me|tell me|can you|could you|"
    r"how many|did i|have i|was my|were my|what (did|was)|where did|"
    r"total (spend|spent)|spending (on|for)|sum of|breakdown|summary)\b"
)
QUESTION_PATTERN = re.compile(QUESTION_STARTS, re.I)


def _is_question(text: str) -> bool:
    """True if message looks like a question about data, not an expense to log."""
    t = (text or "").strip()
    if not t or len(t) < 3:
        return False
    if t.endswith("?"):
        return True
    if QUESTION_PATTERN.match(t):
        return True
    return False


def handle_chat_message(
    message: str,
    source_type: str = "chat",
    user_id: str = None,
    history: list = None,
) -> dict:
    """
    Process one chat message: either add an expense or answer a question.
    Returns a dict suitable for JSON response:
    - type: "expense_added" -> expense, message
    - type: "answer" -> answer_text, question, refused?, rows?
    """
    msg = (message or "").strip()
    if not msg:
        return {"type": "answer", "answer_text": "Send a message to add an expense, ask a question, or try \"Help\" to see what I can do.", "question": ""}

    # 1) Try app actions (limits, goals, affordability, forecast, alerts, Gmail, help, etc.)
    try:
        import chat_actions as ca
        action_result = ca.try_action(msg, user_id=user_id)
        if action_result is not None:
            return {
                "type": "answer",
                "answer_text": action_result.get("message", "Done."),
                "question": msg,
                "refused": False,
                "rows": [],
                "aggregates": None,
            }
    except Exception:
        pass

    if _is_question(msg):
        import nl_query_service as nq
        result = nq.answer_question(msg, conversation_history=history or [])
        return {
            "type": "answer",
            "answer_text": result.get("answer_text", ""),
            "question": result.get("question", msg),
            "refused": result.get("refused", False),
            "rows": result.get("rows", []),
            "aggregates": result.get("aggregates"),
        }

    # Try to add as expense
    try:
        result = extraction_service.extract_expense(msg, source_type=source_type)
    except Exception:
        result = None

    if result and getattr(result, "amount", 0) and getattr(result, "category", ""):
        # Save expense
        confidence = getattr(result, "confidence_score", 0) or 0
        is_verified = 1 if is_auto_verified(confidence) else 0
        expense_id = database.save_expense(
            date=result.date,
            category=result.category,
            amount=result.amount,
            currency=getattr(result, "currency", "USD") or "USD",
            raw_text=msg,
            merchant=getattr(result, "merchant", None),
            subcategory=getattr(result, "subcategory", None),
            source_type=source_type,
            confidence_score=confidence,
            is_verified=is_verified,
            extracted_json=json.dumps(result.extracted_json) if getattr(result, "extracted_json", None) else None,
            correction_json=None,
            user_id=user_id,
        )
        if result.merchant and result.category and confidence >= 0.6:
            import merchant_service
            merchant_service.remember_merchant_mapping(
                result.merchant,
                result.category,
                subcategory=result.subcategory,
                display_name=result.merchant,
                confidence_score=confidence,
            )
        row = database.get_expense(expense_id)
        if row:
            expense_data = {
                "id": row.get("id"),
                "date": row.get("date"),
                "category": row.get("category"),
                "amount": row.get("amount"),
                "currency": row.get("currency"),
                "raw_text": (row.get("raw_text") or "")[:80],
            }
            reply = f"Added: {row.get('date')} · {row.get('category')} · {row.get('currency', 'USD')} {float(row.get('amount', 0)):.2f}"
            if row.get("raw_text"):
                reply += f"\n\"{(row.get('raw_text') or '')[:60]}{'…' if len(row.get('raw_text') or '') > 60 else ''}\""
        else:
            expense_data = {"date": result.date, "category": result.category, "amount": result.amount, "currency": getattr(result, "currency", "USD"), "raw_text": msg[:80]}
            reply = f"Added: {result.date} · {result.category} · {getattr(result, 'currency', 'USD')} {result.amount:.2f}"
        return {"type": "expense_added", "expense": expense_data, "message": reply}
    else:
        # Fallback: treat as question
        import nl_query_service as nq
        result = nq.answer_question(msg, conversation_history=history or [])
        return {
            "type": "answer",
            "answer_text": result.get("answer_text", "I couldn't log that as an expense. Try: \"$50 on groceries yesterday\" or ask: \"How much did I spend on food?\"."),
            "question": result.get("question", msg),
            "refused": result.get("refused", False),
            "rows": result.get("rows", []),
            "aggregates": result.get("aggregates"),
        }
