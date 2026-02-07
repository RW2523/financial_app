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
