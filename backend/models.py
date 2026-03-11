from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ExpenseInput(BaseModel):
    text: str


class ExpenseExtracted(BaseModel):
    date: str
    category: str
    amount: float
    currency: str = "USD"
    raw_text: str


class ExpenseResponse(BaseModel):
    id: int
    date: str
    category: str
    amount: float
    currency: str
    raw_text: str
    created_at: str


class MonthlyRequest(BaseModel):
    year: int = Field(default_factory=lambda: datetime.now().year)
    month: int = Field(default_factory=lambda: datetime.now().month)


class LimitSet(BaseModel):
    category: str  # e.g. "food", "transport", "total"
    amount: float
    currency: str = "USD"


class GmailSyncRequest(BaseModel):
    query: str = "newer_than:7d (from:paypal.com OR from:amazon.com OR from:uber.com OR subject:receipt OR subject:payment OR subject:order)"
    max_results: int = 30
