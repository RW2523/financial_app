from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import database
import llm_service
import audio_service
from models import ExpenseInput, ExpenseResponse, MonthlyRequest, LimitSet, GmailSyncRequest
import os
import tempfile

NEAR_LIMIT_PERCENT = 80  # Alert when spending >= 80% of limit

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
    """Add expense from text description"""
    try:
        # Extract structured data using LLM
        extracted = llm_service.extract_expense_data(expense_input.text)

        # Save to database
        expense_id = database.save_expense(
            date=extracted["date"],
            category=extracted["category"],
            amount=extracted["amount"],
            currency=extracted["currency"],
            raw_text=expense_input.text
        )

        # Return saved expense
        return database.get_expense(expense_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add-audio-expense", response_model=ExpenseResponse)
async def add_audio_expense(file: UploadFile = File(...)):
    """Add expense from audio file"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name

        # Transcribe audio to text
        transcribed_text = audio_service.transcribe_audio(temp_audio_path)

        # Clean up temp file
        os.unlink(temp_audio_path)

        # Extract structured data using LLM
        extracted = llm_service.extract_expense_data(transcribed_text)

        # Save to database
        expense_id = database.save_expense(
            date=extracted["date"],
            category=extracted["category"],
            amount=extracted["amount"],
            currency=extracted["currency"],
            raw_text=transcribed_text
        )

        # Return saved expense
        return database.get_expense(expense_id)

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
