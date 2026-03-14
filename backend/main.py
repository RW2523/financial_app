from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import database
import llm_service
import audio_service
import extraction_service
from models import ExpenseInput, ExpenseResponse, MonthlyRequest, LimitSet, GmailSyncRequest, VerifyExpenseRequest, AskRequest, AskResponse, ChatRequest, GoalCreate, GoalUpdate, AffordabilityRequest, AffordabilityResponse, ClearDataRequest, SimulateRequest, SimulateResponse
import os
import tempfile

from config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, is_auto_verified, NEAR_LIMIT_PERCENT, DEFAULT_USER_ID


def _user_id() -> str:
    """Current user id (single-user mode: always default). Replace with auth context for multi-user."""
    return DEFAULT_USER_ID

app = FastAPI(title="Expense Tracker API")

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup. Whisper loads on first audio request."""
    database.init_database()
    print("✅ Database initialized")
    print("✅ Ready to accept requests (Whisper loads on first voice input)")


@app.get("/")
async def root():
    return {"message": "Expense Tracker API", "status": "running"}


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
        return chat_service.handle_chat_message(body.message.strip(), source_type="chat", user_id=_user_id())
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
    Add sample expenses (last 4 months), limits, and goals so the app makes sense with all elements.
    """
    try:
        import seed_data
        result = seed_data.load_sample_data(user_id=_user_id())
        return {"ok": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seed sample data failed: {str(e)}")


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
        return {
            "configured": has_creds and has_token,
            "credentials_path": gs.CREDENTIALS_PATH,
            "token_path": gs.TOKEN_PATH,
        }
    except Exception as e:
        return {"configured": False, "error": str(e)}


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
