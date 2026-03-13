"""
Expense service: facade over database with current user context.
Use this layer for all expense read/write so multi-user auth can inject user_id in one place.
"""
from typing import List, Dict, Optional
import database
from context import get_current_user_id


def save_expense(
    date: str,
    category: str,
    amount: float,
    currency: str,
    raw_text: str,
    *,
    merchant: str = None,
    subcategory: str = None,
    source_type: str = None,
    confidence_score: float = None,
    is_verified: int = 1,
    extracted_json: str = None,
    correction_json: str = None,
) -> int:
    return database.save_expense(
        date, category, amount, currency, raw_text,
        merchant=merchant,
        subcategory=subcategory,
        source_type=source_type,
        confidence_score=confidence_score,
        is_verified=is_verified,
        extracted_json=extracted_json,
        correction_json=correction_json,
        user_id=get_current_user_id(),
    )


def get_expense(expense_id: int) -> Optional[Dict]:
    return database.get_expense(expense_id)


def get_monthly_expenses(year: int, month: int) -> List[Dict]:
    return database.get_monthly_expenses(year, month, user_id=get_current_user_id())


def get_all_expenses() -> List[Dict]:
    return database.get_all_expenses(user_id=get_current_user_id())


def get_expenses_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    return database.get_expenses_by_date_range(start_date, end_date, user_id=get_current_user_id())


def query_expenses_safe(**kwargs) -> List[Dict]:
    return database.query_expenses_safe(**kwargs, user_id=get_current_user_id())


def get_expenses_for_review(confidence_threshold: float = 0.6) -> List[Dict]:
    return database.get_expenses_for_review(confidence_threshold=confidence_threshold, user_id=get_current_user_id())


def update_expense(expense_id: int, **kwargs) -> None:
    database.update_expense(expense_id, **kwargs)


def delete_expense(expense_id: int) -> bool:
    return database.delete_expense(expense_id)
