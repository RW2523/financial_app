from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import database
import llm_service
import audio_service
from models import ExpenseInput, ExpenseResponse, MonthlyRequest
import os
import tempfile

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
