from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import json
import database
import llm_service
import audio_service
import extraction_service
from models import (
    ExpenseInput, ExpenseResponse, MonthlyRequest, LimitSet, GmailSyncRequest,
    VerifyExpenseRequest, AskRequest, AskResponse, ChatRequest,
    AuthRegisterRequest, AuthLoginRequest, AuthUserResponse,
    GoalCreate, GoalUpdate, AffordabilityRequest, AffordabilityResponse,
    ClearDataRequest, SimulateRequest, SimulateResponse,
    SalaryCreate, SalaryUpdate, InvestmentTransactionCreate, InvestmentTransactionUpdate,
    StockDetailsRequest, StockDetailsResponse, StockAffordabilityRequest, StockAffordabilityResponse,
)
import os
import tempfile

from config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, is_auto_verified, NEAR_LIMIT_PERCENT, DEFAULT_USER_ID
import context as request_context


def _user_id() -> str:
    """Current user id from request (X-User-Id header) or default."""
    return request_context.get_current_user_id()


class UserIdMiddleware(BaseHTTPMiddleware):
    """Set request user id from X-User-Id header for all API calls."""
    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-Id", "").strip() or None
        request_context.set_current_user_id(user_id)
        try:
            return await call_next(request)
        finally:
            request_context.set_current_user_id(None)


app = FastAPI(title="Expense Tracker API")

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(UserIdMiddleware)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup. Whisper loads on first audio request."""
    database.init_database()
    print("✅ Database initialized")
    print("✅ Ready to accept requests (Whisper loads on first voice input)")


@app.get("/")
async def root():
    return {"message": "Expense Tracker API", "status": "running"}


# ---------- Auth (login / register) ----------

@app.get("/auth/status")
async def auth_status():
    """Health check for auth module. Returns 200 if this API has auth routes (e.g. for login page)."""
    return {"auth": True}


@app.post("/auth/register", response_model=AuthUserResponse)
async def auth_register(body: AuthRegisterRequest):
    """Register a new user with username, password, and optional salary/budget."""
    try:
        import auth_service
        user = auth_service.register(
            username=body.username,
            password=body.password,
            salary=body.salary,
            monthly_budget=body.monthly_budget,
            currency=body.currency or "USD",
        )
        return AuthUserResponse(
            user_id=user["id"],
            username=user.get("username", body.username),
            salary=float(user.get("salary") or 0),
            monthly_budget=float(user.get("monthly_budget") or 0),
            currency=user.get("currency") or "USD",
            display_name=user.get("display_name"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", response_model=AuthUserResponse)
async def auth_login(body: AuthLoginRequest):
    """Login with username and password. Returns user profile (no token; send X-User-Id with user_id on subsequent requests)."""
    import auth_service
    import seed_data
    user = auth_service.login(username=body.username.strip(), password=body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    user_id = user["id"]
    # For demo user: ensure they have sample data so "Default login" gives a full experience
    if user_id == "demo":
        try:
            count = database.get_expense_count_for_user(user_id)
            if count == 0:
                seed_data.load_sample_data(user_id=user_id)
        except Exception:
            pass
    return AuthUserResponse(
        user_id=user_id,
        username=user.get("username", ""),
        salary=float(user.get("salary") or 0),
        monthly_budget=float(user.get("monthly_budget") or 0),
        currency=user.get("currency") or "USD",
        display_name=user.get("display_name"),
    )


@app.post("/add-text-expense", response_model=ExpenseResponse)
async def add_text_expense(expense_input: ExpenseInput):
    """Add expense from text description (hybrid extraction: rules + LLM fallback)."""
    try:
        source = expense_input.source_type or "web_text"
        result = extraction_service.extract_expense(expense_input.text, source_type=source)

        is_verified = 1 if is_auto_verified(result.confidence_score) else 0
        expense_id = database.save_expense(
            date=result.date,
            category=result.category,
            amount=result.amount,
            currency=result.currency,
            raw_text=expense_input.text,
            merchant=result.merchant,
            subcategory=result.subcategory,
            source_type=source,
            confidence_score=result.confidence_score,
            is_verified=is_verified,
            extracted_json=json.dumps(result.extracted_json) if result.extracted_json else None,
            correction_json=None,
        )
        if result.merchant and result.category and (result.confidence_score or 0) >= 0.6:
            import merchant_service
            merchant_service.remember_merchant_mapping(
                result.merchant,
                result.category,
                subcategory=result.subcategory,
                display_name=result.merchant,
                confidence_score=result.confidence_score or 0,
            )
        row = database.get_expense(expense_id)
        return _row_to_response(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _row_to_response(row: dict) -> ExpenseResponse:
    """Build ExpenseResponse from DB row (supports legacy rows without new columns)."""
    if row is None:
        raise ValueError("No expense row")
    return ExpenseResponse(
        id=row["id"],
        date=row["date"],
        category=row["category"],
        amount=float(row["amount"]),
        currency=row["currency"] or "USD",
        raw_text=row.get("raw_text"),
        created_at=row.get("created_at"),
        merchant=row.get("merchant"),
        subcategory=row.get("subcategory"),
        source_type=row.get("source_type"),
        confidence_score=row.get("confidence_score"),
        is_verified=row.get("is_verified"),
        extracted_json=row.get("extracted_json"),
        correction_json=row.get("correction_json"),
    )


@app.post("/add-audio-expense", response_model=ExpenseResponse)
async def add_audio_expense(file: UploadFile = File(...)):
    """Add expense from audio file (hybrid extraction after Whisper)."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        transcribed_text = audio_service.transcribe_audio(temp_audio_path)
        os.unlink(temp_audio_path)

        result = extraction_service.extract_expense(transcribed_text, source_type="web_voice")

        is_verified = 1 if is_auto_verified(result.confidence_score) else 0
        expense_id = database.save_expense(
            date=result.date,
            category=result.category,
            amount=result.amount,
            currency=result.currency,
            raw_text=transcribed_text,
            merchant=result.merchant,
            subcategory=result.subcategory,
            source_type="web_voice",
            confidence_score=result.confidence_score,
            is_verified=is_verified,
            extracted_json=json.dumps(result.extracted_json) if result.extracted_json else None,
            correction_json=None,
        )
        if result.merchant and result.category and (result.confidence_score or 0) >= 0.6:
            import merchant_service
            merchant_service.remember_merchant_mapping(
                result.merchant,
                result.category,
                subcategory=result.subcategory,
                display_name=result.merchant,
                confidence_score=result.confidence_score or 0,
            )
        return _row_to_response(database.get_expense(expense_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add-document-expenses")
async def add_document_expenses(
    files: list[UploadFile] = File(...),
    message: str | None = Form(None),
):
    """
    Add expenses from uploaded PDFs and/or images (receipts, invoices).
    Uses OCR for images and text extraction for PDFs; LLM extracts all expense lines.
    """
    import document_service
    if not files:
        raise HTTPException(status_code=400, detail="At least one file (PDF or image) is required.")
    combined_text_parts = []
    for up in files:
        ct = up.content_type or ""
        fn = up.filename or ""
        suffix = ".pdf" if ("pdf" in ct or fn.lower().endswith(".pdf")) else ".img"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await up.read()
            tmp.write(content)
            tmp_path = tmp.name
        try:
            text = document_service.get_text_from_file(tmp_path, ct, fn)
            if text:
                combined_text_parts.append(f"--- {fn}\n{text}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    combined_text = "\n\n".join(combined_text_parts) if combined_text_parts else ""
    if not combined_text.strip():
        return {
            "added": 0,
            "expenses": [],
            "message": "No text could be extracted from the files. For images install easyocr; for PDFs install pymupdf.",
            "ocr_available": document_service.OCR_AVAILABLE,
            "pdf_available": document_service.PDF_AVAILABLE,
        }
    expenses_data = llm_service.extract_expenses_from_document(combined_text)
    uid = _user_id()
    added = []
    for exp in expenses_data:
        try:
            eid = database.save_expense(
                date=exp["date"],
                category=exp["category"],
                amount=exp["amount"],
                currency=exp.get("currency") or "USD",
                raw_text=message or "From uploaded document",
                merchant=exp.get("merchant"),
                subcategory=None,
                source_type="document_upload",
                confidence_score=0.7,
                is_verified=0,
                extracted_json=None,
                correction_json=None,
                user_id=uid,
            )
            row = database.get_expense(eid)
            if row:
                added.append(_row_to_response(row))
        except Exception:
            continue
    return {
        "added": len(added),
        "expenses": added,
        "message": f"Added {len(added)} expense(s) from your document(s)." if added else "No expenses could be extracted from the document text.",
        "ocr_available": document_service.OCR_AVAILABLE,
        "pdf_available": document_service.PDF_AVAILABLE,
    }


@app.post("/monthly-summary")
async def monthly_summary(request: MonthlyRequest):
    """Get AI-generated monthly expense summary"""
    try:
        expenses = database.get_monthly_expenses(request.year, request.month)
        summary = llm_service.generate_monthly_summary(expenses)

        return {
            "year": request.year,
            "month": request.month,
            "total_expenses": len(expenses),
            "summary": summary,
            "expenses": expenses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/expenses")
async def get_all_expenses():
    """Get all expenses"""
    return database.get_all_expenses()


@app.get("/expenses/review")
async def get_expenses_for_review(confidence_below: float = None):
    """
    Return expenses needing verification: is_verified = false or confidence below threshold.
    Optional query param confidence_below overrides default (CONFIDENCE_MEDIUM).
    """
    threshold = confidence_below if confidence_below is not None else CONFIDENCE_MEDIUM
    return database.get_expenses_for_review(confidence_threshold=threshold)


@app.post("/expenses/{expense_id}/verify", response_model=ExpenseResponse)
async def verify_expense(expense_id: int, body: VerifyExpenseRequest):
    """
    Verify or correct an expense. Accepts optional corrected fields.
    Sets is_verified=1, stores correction_json, and updates merchant memory if merchant/category provided.
    """
    row = database.get_expense(expense_id)
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Build correction payload from provided fields only
    correction = {}
    if body.date is not None:
        correction["date"] = body.date
    if body.category is not None:
        correction["category"] = body.category
    if body.subcategory is not None:
        correction["subcategory"] = body.subcategory
    if body.amount is not None:
        correction["amount"] = body.amount
    if body.currency is not None:
        correction["currency"] = body.currency
    if body.merchant is not None:
        correction["merchant"] = body.merchant

    # Apply updates: use correction values when present, else keep existing
    updates = {
        "is_verified": 1,
        "correction_json": json.dumps(correction) if correction else None,
    }
    if body.date is not None:
        updates["date"] = body.date
    if body.category is not None:
        updates["category"] = body.category
    if body.subcategory is not None:
        updates["subcategory"] = body.subcategory
    if body.amount is not None:
        updates["amount"] = body.amount
    if body.currency is not None:
        updates["currency"] = body.currency
    if body.merchant is not None:
        updates["merchant"] = body.merchant

    database.update_expense(expense_id, **updates)

    # Improve merchant memory from correction (high confidence because user confirmed)
    merchant_val = (body.merchant if body.merchant is not None else row.get("merchant")) or ""
    category_val = (body.category if body.category is not None else row.get("category")) or ""
    if merchant_val and category_val:
        import merchant_service
        merchant_service.remember_merchant_mapping(
            merchant_val.strip(),
            category_val.strip(),
            subcategory=(body.subcategory if body.subcategory is not None else row.get("subcategory")) or None,
            display_name=merchant_val.strip(),
            confidence_score=1.0,
        )

    return _row_to_response(database.get_expense(expense_id))


@app.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int):
    """Remove an expense (e.g. reject from review queue)."""
    if not database.delete_expense(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"ok": True}


# ---------- Expense limits & alerts ----------

def _build_limit_alerts(year: int, month: int) -> list:
    """Return list of { category, limit, spent, percent, alert_type: 'near'|'over' }."""
    limits = database.get_limits()
    spending = database.get_spending_by_category_for_month(year, month)
    alerts = []
    for lim in limits:
        cat = lim["category"]
        limit_amt = float(lim["amount"])
        spent = spending.get(cat, 0.0)
        if limit_amt <= 0:
            continue
        percent = (spent / limit_amt) * 100
        if spent >= limit_amt:
            alerts.append({"category": cat, "limit": limit_amt, "spent": spent, "percent": round(percent, 1), "alert_type": "over"})
        elif percent >= NEAR_LIMIT_PERCENT:
            alerts.append({"category": cat, "limit": limit_amt, "spent": spent, "percent": round(percent, 1), "alert_type": "near"})
    return alerts


@app.get("/limits")
async def list_limits():
    """List all expense limits."""
    return database.get_limits()


@app.post("/limits")
async def set_limit(limit: LimitSet):
    """Set or update a limit (category: 'food', 'transport', 'total', etc.)."""
    database.set_limit(limit.category.strip().lower(), limit.amount, limit.currency or "USD")
    return {"ok": True, "category": limit.category, "amount": limit.amount}


@app.delete("/limits/{category}")
async def delete_limit(category: str):
    """Remove limit for category."""
    if database.delete_limit(category.strip().lower()):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="Limit not found")


@app.get("/limits/status")
async def limits_status(year: int = None, month: int = None):
    """Current month spending vs limits and any near/over alerts."""
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    limits = database.get_limits()
    spending = database.get_spending_by_category_for_month(y, m)
    alerts = _build_limit_alerts(y, m)
    return {
        "year": y,
        "month": m,
        "limits": limits,
        "spending": spending,
        "alerts": alerts,
    }


# ---------- Forecasting & predictive alerts ----------

@app.get("/forecast/month")
async def forecast_month(year: int = None, month: int = None):
    """Projected end-of-month total spend and by-category (pace extrapolation / historical fallback)."""
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    import forecast_service as fs
    return fs.projected_month_end(y, m)


@app.get("/forecast/categories")
async def forecast_categories(year: int = None, month: int = None):
    """Projected category spend for month end."""
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    import forecast_service as fs
    return fs.projected_categories(y, m)


@app.get("/alerts/predictive")
async def predictive_alerts(year: int = None, month: int = None):
    """Predictive overspend alerts: categories projected to exceed limit by month end, with message and optional days until overspend."""
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    import forecast_service as fs
    return fs.predictive_alerts(y, m)


# ---------- Advanced insights ----------

@app.get("/insights/overview")
async def get_insights_overview(start_date: str = None, end_date: str = None):
    """Structured behavioral overview for date range. Defaults: last 30 days."""
    import insights_service as ins
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    end_str = (end_date or end.strftime("%Y-%m-%d"))[:10]
    start_str = (start_date or start.strftime("%Y-%m-%d"))[:10]
    expenses = database.get_expenses_by_date_range(start_str, end_str)
    prev_start, prev_end = ins._prev_period(start_str, end_str)
    prev_expenses = database.get_expenses_by_date_range(prev_start, prev_end) if prev_start and prev_end else None
    recurring_total = ins.get_recurring_monthly_total()
    return ins.compute_overview(
        expenses,
        start_str,
        end_str,
        previous_period_expenses=prev_expenses,
        recurring_monthly_total=recurring_total,
    )


@app.get("/insights/trends")
async def get_insights_trends(months: int = 6):
    """Monthly trends for the last N months."""
    import insights_service as ins
    expenses = database.get_all_expenses()
    return ins.compute_trends(expenses, months=min(max(1, months), 24))


@app.get("/insights/categories")
async def get_insights_categories(start_date: str = None, end_date: str = None):
    """Category breakdown for date range. Defaults: last 30 days."""
    import insights_service as ins
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    end_str = (end_date or end.strftime("%Y-%m-%d"))[:10]
    start_str = (start_date or start.strftime("%Y-%m-%d"))[:10]
    expenses = database.get_expenses_by_date_range(start_str, end_str)
    return ins.compute_categories(expenses, start_str, end_str)


@app.get("/insights/anomalies")
async def get_insights_anomalies(start_date: str = None, end_date: str = None, z_threshold: float = 2.0, top_percentile: float = 95.0):
    """Anomaly detection for date range. Defaults: last 30 days."""
    import insights_service as ins
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    end_str = (end_date or end.strftime("%Y-%m-%d"))[:10]
    start_str = (start_date or start.strftime("%Y-%m-%d"))[:10]
    expenses = database.get_expenses_by_date_range(start_str, end_str)
    return ins.compute_anomalies(expenses, start_str, end_str, z_threshold=z_threshold, top_percentile=top_percentile)


@app.get("/insights/narrative")
async def get_insights_narrative(start_date: str = None, end_date: str = None):
    """Optional LLM narrative from precomputed overview insights."""
    import insights_service as ins
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    end_str = (end_date or end.strftime("%Y-%m-%d"))[:10]
    start_str = (start_date or start.strftime("%Y-%m-%d"))[:10]
    expenses = database.get_expenses_by_date_range(start_str, end_str)
    prev_start, prev_end = ins._prev_period(start_str, end_str)
    prev_expenses = database.get_expenses_by_date_range(prev_start, prev_end) if prev_start and prev_end else None
    recurring_total = ins.get_recurring_monthly_total()
    overview = ins.compute_overview(
        expenses, start_str, end_str,
        previous_period_expenses=prev_expenses,
        recurring_monthly_total=recurring_total,
    )
    narrative = ins.generate_insights_narrative(overview)
    return {"start_date": start_str, "end_date": end_str, "overview": overview, "narrative": narrative}


@app.get("/insights/health-score")
async def get_health_score(year: int = None, month: int = None):
    """Budget health score 0-100 from weighted metrics (adherence, overspend frequency, volatility, recurring burden, discretionary ratio, anomaly frequency)."""
    import health_service as hs
    now = datetime.now()
    y, m = year or now.year, month or now.month
    return hs.compute_health_score(y, m)


@app.get("/insights/recommendations")
async def get_recommendations(year: int = None, month: int = None, use_llm: bool = False):
    """Grounded recommendation cards (metric_cited, value, suggestion). Optional use_llm rephrases suggestion text only."""
    import health_service as hs
    now = datetime.now()
    y, m = year or now.year, month or now.month
    recs = hs.generate_recommendations(y, m)
    if use_llm:
        recs = hs.recommendations_with_optional_llm(recs)
    return {"year": y, "month": m, "recommendations": recs}


# ---------- Natural language query (Ask AI) ----------

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Safe NL query over expense data. Returns parsed query, answer text, and supporting rows.
    Only answers from DB data; refuses financial advice / out-of-scope questions.
    """
    import nl_query_service as nq
    result = nq.answer_question(request.question.strip())
    return AskResponse(
        question=result["question"],
        parsed_query=result["parsed_query"],
        answer_text=result["answer_text"],
        rows=result["rows"],
        aggregates=result.get("aggregates"),
        refused=result.get("refused", False),
    )


# ---------- Unified chat (add + ask) ----------

@app.post("/chat")
async def chat_message(body: ChatRequest):
    """
    Single endpoint: add an expense from text or get an answer to a question.
    If the message looks like a question (e.g. 'How much did I spend?') -> answer from data.
    Otherwise treat as expense description and add it.
    """
    try:
        import chat_service
        history = [{"role": m.role, "content": m.content} for m in (body.history or [])]
        return chat_service.handle_chat_message(
            body.message.strip(), source_type="chat", user_id=_user_id(), history=history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat-voice")
async def chat_voice(file: UploadFile = File(...)):
    """
    Transcribe audio, then process as chat (add expense or answer question).
    Returns { transcript, type, ... } with same response shape as /chat.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        transcript = audio_service.transcribe_audio(temp_audio_path)
        os.unlink(temp_audio_path)
        import chat_service
        out = chat_service.handle_chat_message(transcript, source_type="chat_voice", user_id=_user_id())
        out["transcript"] = transcript
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Recurring insights ----------

@app.get("/insights/recurring")
async def get_recurring_insights():
    """Return detected recurring expenses (from last recompute)."""
    rows = database.get_recurring_expenses()
    return [dict(r) for r in rows]


@app.post("/insights/recurring/recompute")
async def recompute_recurring_insights():
    """Recompute recurring patterns from current expenses and return new list."""
    import recurring_service
    detected = recurring_service.recompute_recurring()
    return {"count": len(detected), "recurring": detected}


# ---------- Goals ----------

@app.get("/goals")
async def list_goals(status: str = "active"):
    """List goals (default: active; use status=all for all) with distance and suggested reduction."""
    try:
        import goal_service as gs
        use_status = None if status in (None, "", "all") else (status or "active")
        return gs.get_goals(status=use_status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Goals list failed: {str(e)}")


@app.post("/goals")
async def create_goal_endpoint(body: GoalCreate):
    """Create a new financial goal."""
    try:
        import goal_service as gs
        return gs.create_goal(
            goal_type=body.goal_type,
            target_amount=body.target_amount,
            current_amount=body.current_amount,
            target_date=body.target_date,
            category=body.category,
            description=body.description,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create goal failed: {str(e)}")


@app.put("/goals/{goal_id}")
async def update_goal_endpoint(goal_id: int, body: GoalUpdate):
    """Update a goal (partial fields)."""
    row = database.get_goal(goal_id)
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")
    updates = {}
    if body.goal_type is not None:
        updates["goal_type"] = body.goal_type
    if body.target_amount is not None:
        updates["target_amount"] = body.target_amount
    if body.current_amount is not None:
        updates["current_amount"] = body.current_amount
    if body.target_date is not None:
        updates["target_date"] = body.target_date
    if body.category is not None:
        updates["category"] = body.category
    if body.description is not None:
        updates["description"] = body.description
    if body.status is not None:
        updates["status"] = body.status
    try:
        if not updates:
            import goal_service as gs
            return gs.get_goal_enriched(goal_id)
        database.update_goal(goal_id, **updates)
        import goal_service as gs
        return gs.get_goal_enriched(goal_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update goal failed: {str(e)}")


@app.delete("/goals/{goal_id}")
async def delete_goal_endpoint(goal_id: int):
    """Delete a goal."""
    if not database.delete_goal(goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"ok": True}


# ---------- Affordability check ----------

@app.post("/affordability/check", response_model=AffordabilityResponse)
async def check_affordability_endpoint(body: AffordabilityRequest):
    """Advanced 'can I afford this?' using limits, projected spend, recurring, and goals."""
    try:
        import affordability_service as aff
        result = aff.check_affordability(amount=body.amount, category=body.category, merchant=body.merchant)
        return AffordabilityResponse(
            can_afford=result["can_afford"],
            reasons=result["reasons"],
            projected_impact=result.get("projected_impact"),
            budget_impact=result.get("budget_impact"),
            goal_impact=result.get("goal_impact"),
            recommendation_text=result.get("recommendation_text", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Affordability check failed: {str(e)}")


# ---------- Scenario simulator ----------

@app.post("/simulate", response_model=SimulateResponse)
async def simulate_scenario(body: SimulateRequest):
    """Run financial scenario simulation. Does not modify any data."""
    try:
        import simulator_service as sim
        adjustments = [a.model_dump() for a in body.adjustments]
        result = sim.run_simulation(adjustments, year=body.year, month=body.month)
        return SimulateResponse(
            baseline_summary=result["baseline_summary"],
            simulated_summary=result["simulated_summary"],
            delta_summary=result["delta_summary"],
            projected_limit_changes=result["projected_limit_changes"],
            goal_impact=result["goal_impact"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


# ---------- Clear all data (Settings) ----------

@app.post("/admin/clear-data")
async def clear_all_data_endpoint(body: ClearDataRequest):
    """
    Delete all expenses, limits, goals, recurring, and gmail_processed for the current user.
    Requires body: { "confirm": true }. Returns counts of deleted rows.
    """
    if body.confirm is not True:
        raise HTTPException(status_code=400, detail="Send { \"confirm\": true } to clear all data.")
    try:
        counts = database.clear_all_data(_user_id())
        return {"ok": True, "deleted": counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear data failed: {str(e)}")


@app.post("/admin/seed-sample-data")
async def seed_sample_data_endpoint():
    """
    Add sample expenses (last 4 months), limits, goals, and Wealth Hub data (salary, investments, watchlist, liability).
    """
    try:
        import seed_data
        result = seed_data.load_sample_data(user_id=_user_id())
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seed sample data failed: {str(e)}")


# ---------- Wealth Hub ----------

@app.get("/wealth/salary")
async def list_salary(year: int = None, month: int = None):
    """List salary records; optional year/month filter."""
    records = database.list_salary_records(user_id=_user_id())
    if year is not None and month is not None:
        records = [r for r in records if (r.get("date") or "")[:7] == f"{year}-{month:02d}"]
    return records


@app.post("/wealth/salary")
async def create_salary(body: SalaryCreate):
    """Create a salary/income record."""
    row = database.create_salary_record(
        date=body.date,
        source=body.source,
        gross_amount=body.gross_amount,
        deductions=body.deductions,
        net_amount=body.net_amount,
        bonus_amount=body.bonus_amount or 0,
        notes=body.notes,
        user_id=_user_id(),
    )
    return row


@app.get("/wealth/salary/summary")
async def salary_summary(year: int = None, month: int = None):
    """Monthly income summary (net + bonus) for the given month."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    return database.get_monthly_income_summary(y, m, user_id=_user_id())


@app.get("/wealth/salary/{record_id}")
async def get_salary(record_id: int):
    """Get one salary record."""
    row = database.get_salary_record(record_id, user_id=_user_id())
    if not row:
        raise HTTPException(status_code=404, detail="Salary record not found")
    return row


@app.put("/wealth/salary/{record_id}")
async def update_salary(record_id: int, body: SalaryUpdate):
    """Update a salary record."""
    row = database.get_salary_record(record_id, user_id=_user_id())
    if not row:
        raise HTTPException(status_code=404, detail="Salary record not found")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    database.update_salary_record(record_id, **updates)
    return database.get_salary_record(record_id, user_id=_user_id())


@app.delete("/wealth/salary/{record_id}")
async def delete_salary(record_id: int):
    """Delete a salary record."""
    if not database.delete_salary_record(record_id, user_id=_user_id()):
        raise HTTPException(status_code=404, detail="Salary record not found")
    return {"ok": True}


@app.get("/wealth/investments")
async def list_investments():
    """List all investment transactions for the current user."""
    return database.list_investment_transactions(user_id=_user_id())


@app.post("/wealth/investments")
async def create_investment(body: InvestmentTransactionCreate):
    """Create an investment transaction (BUY/SELL/DIVIDEND)."""
    row = database.create_investment_transaction(
        ticker=body.ticker,
        stock_name=body.stock_name,
        transaction_type=body.transaction_type,
        quantity=body.quantity,
        price=body.price,
        fees=body.fees or 0,
        date=body.date,
        broker=body.broker,
        notes=body.notes,
        user_id=_user_id(),
    )
    return row


@app.get("/wealth/investments/{tx_id}")
async def get_investment(tx_id: int):
    """Get one investment transaction."""
    row = database.get_investment_transaction(tx_id, user_id=_user_id())
    if not row:
        raise HTTPException(status_code=404, detail="Investment transaction not found")
    return row


@app.put("/wealth/investments/{tx_id}")
async def update_investment(tx_id: int, body: InvestmentTransactionUpdate):
    """Update an investment transaction."""
    row = database.get_investment_transaction(tx_id, user_id=_user_id())
    if not row:
        raise HTTPException(status_code=404, detail="Investment transaction not found")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    database.update_investment_transaction(tx_id, **updates)
    return database.get_investment_transaction(tx_id, user_id=_user_id())


@app.delete("/wealth/investments/{tx_id}")
async def delete_investment(tx_id: int):
    """Delete an investment transaction."""
    if not database.delete_investment_transaction(tx_id, user_id=_user_id()):
        raise HTTPException(status_code=404, detail="Investment transaction not found")
    return {"ok": True}


@app.get("/wealth/portfolio")
async def portfolio_summary():
    """Portfolio holdings and summary (from transactions; current prices from mock/provider)."""
    import wealth_portfolio_service as wps
    import wealth_stock_service as wss
    uid = _user_id()
    transactions = database.list_investment_transactions(user_id=uid)
    tickers = list({(t.get("ticker") or "").strip().upper() for t in transactions if (t.get("ticker") or "").strip()})
    current_prices = wss.get_current_prices_for_tickers(tickers)
    return wps.get_portfolio_summary(user_id=uid, current_prices=current_prices, include_enrichment=True)


@app.get("/wealth/manager")
async def portfolio_manager():
    """Portfolio Manager: allocation by sector, diversification score, stocks that work for you, rebalancing."""
    import wealth_stock_service as wss
    return wss.get_portfolio_manager_view(user_id=_user_id())


@app.get("/wealth/cashflow")
async def cashflow_summary(year: int = None, month: int = None):
    """Monthly cashflow: income, expenses, invested, net savings, free cash, ratios."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    import wealth_cashflow_service as cf
    return cf.get_cashflow_summary(y, m, user_id=_user_id())


@app.get("/wealth/projections")
async def projections(
    year: int = None,
    month: int = None,
    portfolio_growth_mode: str = "moderate",
    monthly_investment_override: float = None,
    expense_growth_pct: float = None,
    salary_growth_pct: float = None,
    target_buffer: float = None,
):
    """Projected expenses, surplus, yearly invested, portfolio projection (6m/1y/3y), scenarios."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    import wealth_projections_service as wproj
    return wproj.get_projections(
        y, m, user_id=_user_id(),
        portfolio_growth_mode=portfolio_growth_mode or "moderate",
        monthly_investment_override=monthly_investment_override,
        expense_growth_pct=expense_growth_pct,
        salary_growth_pct=salary_growth_pct,
        target_buffer=target_buffer,
    )


@app.get("/wealth/suggestions")
async def suggestions(year: int = None, month: int = None):
    """Grounded suggestions from app data (expense ratio, concentration, free cash, etc.)."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    import wealth_suggestions_service as wsug
    return wsug.get_suggestions(y, m, user_id=_user_id())


@app.get("/wealth/overview")
async def wealth_overview(year: int = None, month: int = None):
    """Aggregated overview: summary strip, priority alerts, next actions, wealth score, net worth and goals preview."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    import wealth_overview_service as wov
    return wov.get_overview(user_id=_user_id(), year=y, month=m)


@app.get("/wealth/score")
async def wealth_score():
    """Wealth / Money Health Score 0-100 with contributing factors."""
    import wealth_score_service as ws
    return ws.compute_wealth_score(user_id=_user_id())


@app.get("/wealth/net-worth")
async def net_worth(year: int = None, month: int = None):
    """Net worth: assets (free cash + portfolio) minus liabilities."""
    now = datetime.now()
    y, m = year or now.year, month or now.month
    import wealth_networth_service as nw
    return nw.get_net_worth(user_id=_user_id(), year=y, month=m)


@app.get("/wealth/watchlist")
async def list_watchlist():
    """List watchlist items."""
    return database.list_watchlist(user_id=_user_id())


@app.post("/wealth/watchlist")
async def add_watchlist_item(body: dict):
    """Add or update watchlist item (ticker required; stock_name, target_buy_price, current_price, sector, notes optional)."""
    ticker = (body.get("ticker") or "").strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    wid = database.add_watchlist_item(
        ticker,
        stock_name=body.get("stock_name"),
        target_buy_price=body.get("target_buy_price"),
        current_price=body.get("current_price"),
        sector=body.get("sector"),
        notes=body.get("notes"),
        user_id=_user_id(),
    )
    row = next((r for r in database.list_watchlist(user_id=_user_id()) if r.get("id") == wid or r.get("ticker") == ticker), None)
    return row or {"id": wid, "ticker": ticker}


@app.put("/wealth/watchlist/{item_id}")
async def update_watchlist_item(item_id: int, body: dict):
    """Update watchlist item (target_buy_price, current_price, notes)."""
    ok = database.update_watchlist_item(
        item_id,
        target_buy_price=body.get("target_buy_price"),
        current_price=body.get("current_price"),
        notes=body.get("notes"),
        user_id=_user_id(),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    row = next((r for r in database.list_watchlist(user_id=_user_id()) if r.get("id") == item_id), None)
    return row or {"id": item_id}


@app.delete("/wealth/watchlist/{item_id}")
async def delete_watchlist_item(item_id: int):
    """Remove watchlist item."""
    if not database.delete_watchlist_item(item_id, user_id=_user_id()):
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"ok": True}


@app.get("/wealth/liabilities")
async def list_liabilities():
    """List liabilities for net worth."""
    return database.list_liabilities(user_id=_user_id())


@app.post("/wealth/liabilities")
async def create_liability(body: dict):
    """Create liability (name, balance required; liability_type, notes optional)."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    balance = float(body.get("balance", 0))
    lid = database.create_liability(
        name,
        balance,
        liability_type=body.get("liability_type"),
        notes=body.get("notes"),
        user_id=_user_id(),
    )
    row = next((r for r in database.list_liabilities(user_id=_user_id()) if r.get("id") == lid), None)
    return row or {"id": lid, "name": name, "balance": balance}


@app.put("/wealth/liabilities/{liability_id}")
async def update_liability(liability_id: int, body: dict):
    """Update liability."""
    ok = database.update_liability(
        liability_id,
        name=body.get("name"),
        balance=body.get("balance"),
        liability_type=body.get("liability_type"),
        notes=body.get("notes"),
        user_id=_user_id(),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Liability not found")
    row = next((r for r in database.list_liabilities(user_id=_user_id()) if r.get("id") == liability_id), None)
    return row or {"id": liability_id}


@app.delete("/wealth/liabilities/{liability_id}")
async def delete_liability(liability_id: int):
    """Delete liability."""
    if not database.delete_liability(liability_id, user_id=_user_id()):
        raise HTTPException(status_code=404, detail="Liability not found")
    return {"ok": True}


@app.get("/wealth/stock/search")
async def stock_search(q: str = ""):
    """Search/list stocks by ticker or name. Returns list of stock details."""
    import wealth_stock_service as wss
    return wss.search_stocks(query=q)


@app.get("/wealth/stock/diversification")
async def stock_diversification():
    """Best stocks for your case: suggestions to diversify (sectors you don't hold)."""
    import wealth_stock_service as wss
    return wss.get_diversification_suggestions(user_id=_user_id())


@app.get("/wealth/stock/details")
async def stock_details(ticker: str):
    """Stock search/details (mock or provider). Returns ticker, name, sector, price, etc."""
    import wealth_stock_service as wss
    details = wss.get_stock_details(ticker)
    return StockDetailsResponse(**details)


@app.post("/wealth/stock/affordability", response_model=StockAffordabilityResponse)
async def stock_affordability(body: StockAffordabilityRequest):
    """Can I buy this stock? Based on free cash, income, expenses, concentration."""
    import wealth_stock_service as wss
    result = wss.check_stock_affordability(
        body.ticker, body.quantity, body.price_per_share, user_id=_user_id()
    )
    return StockAffordabilityResponse(**result)


# ---------- Finance news (Tavily) ----------

@app.get("/news/finance")
async def get_finance_news(query: str = None, max_results: int = 15, time_range: str = "week"):
    """
    Fetch finance-related news (money, exchange, stocks, economy) via Tavily.
    Set TAVILY_API_KEY in env to enable. Optional: query, max_results (1–20), time_range (day|week|month|year).
    """
    try:
        import news_service
        result = news_service.fetch_finance_news(
            query=query,
            max_results=max_results,
            time_range=time_range if time_range in ("day", "week", "month", "year") else "week",
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Gmail sync ----------

@app.get("/gmail/status")
async def gmail_status():
    """Whether Gmail is configured (credentials + token) and ready to sync."""
    try:
        import gmail_service as gs
        has_creds = os.path.exists(gs.CREDENTIALS_PATH)
        has_token = os.path.exists(gs.TOKEN_PATH)
        connected = has_creds and has_token
        if connected:
            message = "Ready to sync. Click Sync Gmail to fetch emails."
        elif not has_creds:
            message = f"Credentials not found. Add OAuth client JSON at: {gs.CREDENTIALS_PATH}"
        else:
            message = f"Token not found. Run once: python backend/gmail_auth.py (saves to {gs.TOKEN_PATH})"
        return {
            "connected": connected,
            "configured": connected,
            "message": message,
            "credentials_path": gs.CREDENTIALS_PATH,
            "token_path": gs.TOKEN_PATH,
        }
    except Exception as e:
        return {"connected": False, "configured": False, "message": str(e), "error": str(e)}


@app.post("/gmail/sync")
async def gmail_sync(request: GmailSyncRequest):
    """
    Fetch Gmail messages matching query, extract expense from each (LLM), save and mark processed.
    Returns added count and any errors.
    """
    try:
        import gmail_service as gs
        added, errors = gs.sync_gmail(query=request.query.strip(), max_results=min(request.max_results, 100))
        return {"added": added, "errors": errors[:20]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
