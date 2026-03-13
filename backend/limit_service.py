"""
Limit service: facade over database with current user context.
"""
from typing import List, Dict
import database
from context import get_current_user_id


def get_limits() -> List[Dict]:
    return database.get_limits(user_id=get_current_user_id())


def set_limit(category: str, amount: float, currency: str = "USD") -> None:
    database.set_limit(category, amount, currency, user_id=get_current_user_id())


def delete_limit(category: str) -> bool:
    return database.delete_limit(category, user_id=get_current_user_id())
