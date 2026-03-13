"""
Merchant memory: lookup learned category/subcategory, save and update conservatively.
Used by extraction pipeline (prefer memory over rules/LLM) and after saving expenses (learning).
"""
from typing import Optional, Tuple

import database
from extraction_service import normalize_merchant as _normalize_merchant

# Re-export for admin/helpers
def normalize_merchant(raw: str) -> str:
    """Normalize merchant name for lookup and storage."""
    return _normalize_merchant(raw)


def lookup_merchant_mapping(normalized_name: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Look up category and subcategory for a normalized merchant name.
    Checks merchants table and merchant_aliases. Returns (category, subcategory) or None.
    """
    if not normalized_name or not normalized_name.strip():
        return None
    name = normalized_name.strip().lower()
    m = database.get_merchant_by_normalized_name(name)
    if m:
        return (m["default_category"], m.get("subcategory"))
    m = database.get_merchant_by_alias(name)
    if m:
        return (m["default_category"], m.get("subcategory"))
    return None


def remember_merchant_mapping(
    normalized_name: str,
    category: str,
    subcategory: Optional[str] = None,
    display_name: Optional[str] = None,
    confidence_score: float = 0.0,
) -> None:
    """
    Learn or reinforce merchant -> category mapping.
    - If merchant unknown: insert with category/subcategory.
    - If merchant known: increment use_count; update category only with conservative rules (high confidence or low use_count).
    """
    if not normalized_name or not category:
        return
    name = normalize_merchant(normalized_name)
    if not name:
        return
    existing = database.get_merchant_by_normalized_name(name)
    if existing:
        database.increment_merchant_use_count(name)
        database.update_merchant_category_conservative(
            name,
            category,
            subcategory=subcategory,
            confidence_score=confidence_score,
        )
    else:
        database.upsert_merchant(
            normalized_name=name,
            default_category=category,
            display_name=display_name or name,
            subcategory=subcategory,
        )
