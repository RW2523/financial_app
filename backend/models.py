from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any, Dict, List


class ExpenseInput(BaseModel):
    text: str
    source_type: Optional[str] = None  # e.g. web_text, telegram_text, telegram_photo, api_text


class ExtractionEvidence(BaseModel):
    """Which fields came from rules vs LLM."""
    amount_source: str = "unknown"  # "rules" | "llm"
    currency_source: str = "unknown"
    date_source: str = "unknown"
    category_source: str = "unknown"
    merchant_source: str = "unknown"


class ExpenseExtractionResult(BaseModel):
    """Result of hybrid extraction; supports verification and correction metadata."""
    date: str
    category: str
    amount: float
    currency: str = "USD"
    merchant: Optional[str] = None
    subcategory: Optional[str] = None
    raw_text: str = ""
    confidence_score: float = 0.0
    evidence: Optional[ExtractionEvidence] = None
    extracted_json: Optional[Dict[str, Any]] = None  # full extraction payload for correction UI


class ExpenseCreate(BaseModel):
    """Payload to create an expense (from extraction or API)."""
    date: str
    category: str
    amount: float
    currency: str = "USD"
    raw_text: str = ""
    merchant: Optional[str] = None
    subcategory: Optional[str] = None
    source_type: Optional[str] = None
    confidence_score: Optional[float] = None
    is_verified: int = 1
    extracted_json: Optional[Dict[str, Any]] = None
    correction_json: Optional[Dict[str, Any]] = None


class ExpenseRead(BaseModel):
    """Full expense as read from DB (API response shape)."""
    id: int
    date: str
    category: str
    amount: float
    currency: str
    raw_text: Optional[str] = None
    created_at: Optional[str] = None
    merchant: Optional[str] = None
    subcategory: Optional[str] = None
    source_type: Optional[str] = None
    confidence_score: Optional[float] = None
    is_verified: Optional[int] = None
    extracted_json: Optional[str] = None
    correction_json: Optional[str] = None

    class Config:
        from_attributes = True


class ExpenseResponse(BaseModel):
    """API response for a single expense (backward-compatible; new fields optional)."""
    id: int
    date: str
    category: str
    amount: float
    currency: str
    raw_text: Optional[str] = None
    created_at: Optional[str] = None
    merchant: Optional[str] = None
    subcategory: Optional[str] = None
    source_type: Optional[str] = None
    confidence_score: Optional[float] = None
    is_verified: Optional[int] = None
    extracted_json: Optional[str] = None
    correction_json: Optional[str] = None


class MonthlyRequest(BaseModel):
    year: int = Field(default_factory=lambda: datetime.now().year)
    month: int = Field(default_factory=lambda: datetime.now().month)


class LimitSet(BaseModel):
    category: str  # e.g. "food", "transport", "total"
    amount: float
    currency: str = "USD"


class VerifyExpenseRequest(BaseModel):
    """Optional corrected fields when verifying an expense from the review queue."""
    date: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None


class GmailSyncRequest(BaseModel):
    query: str = "newer_than:7d (from:paypal.com OR from:amazon.com OR from:uber.com OR subject:receipt OR subject:payment OR subject:order)"
    max_results: int = 30


# ---------- Natural language query (Ask AI) ----------

class ParsedQuerySchema(BaseModel):
    """Structured query from NL; only safe fields, no raw SQL."""
    intent: str = "sum"  # sum | list | compare | top_category | top_month | merchant_total | category_total
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    merchant: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    limit: int = 50
    sort: str = "date_desc"  # date_desc | date_asc | amount_desc | amount_asc


class AskRequest(BaseModel):
    question: str


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None


class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    salary: float = 0
    monthly_budget: float = 0
    currency: str = "USD"


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    user_id: str
    username: str
    salary: float = 0
    monthly_budget: float = 0
    currency: str = "USD"
    display_name: Optional[str] = None


class AskResponse(BaseModel):
    question: str
    parsed_query: Dict[str, Any]
    answer_text: str
    rows: List[Dict[str, Any]] = []
    aggregates: Optional[Dict[str, Any]] = None
    refused: bool = False  # True if out-of-scope


# ---------- Goals & affordability ----------

class GoalCreate(BaseModel):
    goal_type: str  # savings_target | spending_reduction | category_cap
    target_amount: float
    current_amount: float = 0
    target_date: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class GoalUpdate(BaseModel):
    goal_type: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    target_date: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AffordabilityRequest(BaseModel):
    amount: float
    category: Optional[str] = None
    merchant: Optional[str] = None


class AffordabilityResponse(BaseModel):
    can_afford: bool
    reasons: List[str] = []
    projected_impact: Optional[Dict[str, Any]] = None
    budget_impact: Optional[Dict[str, Any]] = None
    goal_impact: Optional[Dict[str, Any]] = None
    recommendation_text: str = ""


# ---------- Scenario simulator ----------

class SimulateAdjustment(BaseModel):
    """One scenario adjustment. Fields depend on type."""
    type: str  # reduce_category_percent | remove_recurring_merchant | add_one_time_expense | change_category_cap | save_fixed_per_week
    category: Optional[str] = None
    value: Optional[float] = None
    amount: Optional[float] = None
    merchant: Optional[str] = None


class ClearDataRequest(BaseModel):
    confirm: bool = False


class SimulateRequest(BaseModel):
    adjustments: List[SimulateAdjustment]
    year: Optional[int] = None
    month: Optional[int] = None


class SimulateResponse(BaseModel):
    baseline_summary: Dict[str, Any]
    simulated_summary: Dict[str, Any]
    delta_summary: Dict[str, Any]
    projected_limit_changes: List[Dict[str, Any]]
    goal_impact: List[Dict[str, Any]]


# ---------- Wealth Hub ----------

class SalaryCreate(BaseModel):
    date: str
    source: str
    gross_amount: float
    deductions: float = 0
    net_amount: Optional[float] = None
    bonus_amount: float = 0
    notes: Optional[str] = None


class SalaryUpdate(BaseModel):
    date: Optional[str] = None
    source: Optional[str] = None
    gross_amount: Optional[float] = None
    deductions: Optional[float] = None
    net_amount: Optional[float] = None
    bonus_amount: Optional[float] = None
    notes: Optional[str] = None


class InvestmentTransactionCreate(BaseModel):
    ticker: str
    stock_name: Optional[str] = None
    transaction_type: str  # BUY | SELL | DIVIDEND
    quantity: float
    price: float
    fees: float = 0
    date: str
    broker: Optional[str] = None
    notes: Optional[str] = None


class InvestmentTransactionUpdate(BaseModel):
    ticker: Optional[str] = None
    stock_name: Optional[str] = None
    transaction_type: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    fees: Optional[float] = None
    date: Optional[str] = None
    broker: Optional[str] = None
    notes: Optional[str] = None


class StockDetailsRequest(BaseModel):
    ticker: str


class StockDetailsResponse(BaseModel):
    ticker: str
    stock_name: Optional[str] = None
    sector: Optional[str] = None
    current_price: Optional[float] = None
    change: Optional[float] = None
    market_cap: Optional[str] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    range_52w: Optional[str] = None
    source: str = "manual"  # manual | provider


class StockAffordabilityRequest(BaseModel):
    ticker: str
    quantity: float
    price_per_share: float


class StockAffordabilityResponse(BaseModel):
    affordable: bool
    message: str
    free_cash: float
    cost: float
    concentration_risk: Optional[bool] = None
    reasons: List[str] = []
