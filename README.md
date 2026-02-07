# AI Expense Tracker

A voice-enabled expense tracking application with local LLM processing. Add expenses via the **web app** (text or voice), **Telegram**, or export data for **Power BI** / Tableau.

---

## Features

| Feature | Description |
|--------|-------------|
| **Text input** | Type an expense in plain language; LLM extracts date, category, amount, currency. |
| **Voice input** | Record audio in the app; Whisper transcribes, then LLM extracts and saves. |
| **Telegram bot** | Add expenses by text; send a receipt/screenshot (OCR) to add from image; ask for a "report" and get a monthly summary in the chat. |
| **AI extraction** | Ollama (llama3.1) parses natural language into structured fields. |
| **SQLite storage** | All expenses stored in `database/expenses.db`. |
| **Monthly summary** | AI-generated insights for a chosen month. |
| **BI Dashboard** | Interactive Plotly charts (time series, by category, monthly). |
| **Power BI / Tableau** | Download CSV or Excel; embed a Power BI “Publish to web” report in the app. |
| **Public access** | Expose backend and frontend via Cloudflare tunnels (optional). |

---

## Prerequisites

- **Python 3.10+** (3.12 recommended for compatibility with Whisper and dependencies)
- **Ollama** installed and running ([ollama.ai](https://ollama.ai))
- **llama3.1** model: `ollama pull llama3.1`
- (Optional) **Telegram** account for the bot workflow

---

## Setup (one-time)

### 1. Clone or open the project

```bash
cd /path/to/financial_app
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, Streamlit, Ollama/LLM-related packages, Whisper, Plotly, Telegram bot libraries, and the rest. First run may take a few minutes (e.g. PyTorch, Whisper).

### 4. Install and run Ollama (if not already)

```bash
# Install from https://ollama.ai, then:
ollama pull llama3.1
ollama serve   # if not already running
```

---

## Running the application

You need the **backend** running for the web app and Telegram bot to work. The **frontend** is the Streamlit UI. The **Telegram bot** is optional and only needed if you want to add expenses via Telegram.

### Process 1: Start the backend (required for web and Telegram)

From the **project root** (`financial_app/`):

```bash
source venv/bin/activate   # if not already
cd backend
uvicorn main:app --reload --port 8000
```

Or from project root without `cd`:

```bash
uvicorn backend.main:app --reload --port 8000
```

- API base URL: **http://127.0.0.1:8000**
- Interactive docs: **http://127.0.0.1:8000/docs**
- On startup: database is created at `database/expenses.db`; Whisper loads on first voice request.

### Process 2: Start the frontend (web UI)

In a **second terminal**, from project root:

```bash
source venv/bin/activate
cd frontend
streamlit run app.py --server.port 8501
```

- Open in browser: **http://localhost:8501**

If the frontend cannot reach the backend, use the **sidebar → Backend API URL** and set it to `http://127.0.0.1:8000` (or your backend URL).

### Process 3: Load sample data (optional)

To pre-fill the database with sample expenses (e.g. Boston student, 2025 + Jan 2026):

```bash
source venv/bin/activate
python backend/seed_data.py
```

Then in the app, open **View Expenses** or **BI Dashboard** and refresh.

### Process 4: Run the Telegram bot (optional)

Only if you want to add expenses or get reports via Telegram (backend must be running).

1. **Create a bot** (one-time):
   - In Telegram, open **@BotFather**.
   - Send `/newbot`, follow the prompts, and copy the **token** (e.g. `7123456789:AAH...`).
   - Do not commit or share this token.

2. **Run the bot** (in a **third terminal**), from project root:

   ```bash
   source venv/bin/activate
   export TELEGRAM_BOT_TOKEN="your_token_from_botfather"
   export EXPENSE_API_URL="http://127.0.0.1:8000"
   python telegram_bot.py
   ```

   - If the backend is on another host, set `EXPENSE_API_URL` to that URL (e.g. `http://192.168.1.5:8000`).
   - **Receipt/screenshot (OCR):** Install `easyocr` so the bot can read images: `pip install easyocr`. Then send a **photo** of a receipt or screenshot; the bot extracts text, then adds the expense via the same LLM pipeline. If `easyocr` is not installed, the bot still works for text and report.

3. **What you can send the bot:**
   - **Text (expense):** e.g. `50 dollars on groceries yesterday`, `Coffee 5 euros this morning` → bot adds it and replies with the saved record.
   - **Photo (receipt/screenshot):** Attach an image → bot runs OCR, then adds the expense from the extracted text (requires `easyocr`).
   - **Report request:** e.g. `report`, `summary`, `report February`, `report feb 2025` → bot replies with that month’s summary (transaction count, total, top categories, AI summary).
   - Use `/start` or `/help` in the bot for a short reminder.

### Process 5: Public access (optional)

To expose the app over the internet (e.g. for mobile or sharing):

1. Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/).
2. In separate terminals:

   ```bash
   cloudflared tunnel --url http://localhost:8000   # backend
   cloudflared tunnel --url http://localhost:8501   # frontend
   ```

3. Use the generated HTTPS URLs. For Telegram, set `EXPENSE_API_URL` to the public backend URL if the bot runs on a server that can reach it.

---

## Usage (web app)

### Adding expenses

- **Add Expense → Text:** Enter a sentence (e.g. “Spent $45 on groceries yesterday”) and click **Add Text Expense**. The LLM extracts date, category, amount, currency and saves to the DB.
- **Add Expense → Voice:** Click record, speak the expense, stop, then **Process Audio Expense**. Whisper transcribes; then the same extraction and save.
- **Telegram:** Send **text** (e.g. "30 dollars lunch today") or a **photo** of a receipt/screenshot (OCR + LLM add the expense). Ask **"report"** or **"report February 2025"** to get a monthly summary in the chat (backend and bot must be running).

### Viewing expenses

- **View Expenses:** Lists all expenses and shows total count, categories, and total amount. Use **Refresh Expenses** to reload.

### Monthly summary

- **Monthly Summary:** Choose year and month, click **Generate Summary**. The app returns AI-generated insights and the list of expenses for that month (requires Ollama).

### BI Dashboard and Power BI

- **BI Dashboard** tab:
  - If the backend is reachable, expenses load from the API. You can set **From** / **To** dates; KPIs and charts update for that range.
  - If the API is unreachable, you can **upload a CSV** (columns: `date`, `category`, `amount`; optional: `currency`, `raw_text`) to view the same charts.
  - **Download CSV** / **Download Excel** for the current date range. Use these in **Power BI Desktop** or **Tableau** (Get data → Text/CSV or Excel).
  - **Embed Power BI report:** In Power BI, publish your report to the web, copy the embed URL, and paste it in the “Power BI embed URL” field to show the report inside the app.

---

## Backend API (reference)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check; returns `{"message":"Expense Tracker API","status":"running"}`. |
| POST | `/add-text-expense` | Body: `{"text": "..."}`. Extracts and saves expense; returns saved record. |
| POST | `/add-audio-expense` | Form: `file` (audio). Transcribes, extracts, saves; returns saved record. |
| POST | `/monthly-summary` | Body: `{"year": 2025, "month": 6}`. Returns AI summary and expenses for that month. |
| GET | `/expenses` | Returns all expenses (list of objects). |

---

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `EXPENSE_API_URL` | Frontend (Streamlit), Telegram bot | Backend base URL (e.g. `http://127.0.0.1:8000`). Default in app: `http://127.0.0.1:8000`. |
| `TELEGRAM_BOT_TOKEN` | `telegram_bot.py` | Token from @BotFather. Required to run the bot. |

---

## Project structure

```
financial_app/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── database.py          # SQLite init and CRUD
│   ├── llm_service.py       # Ollama (extract + monthly summary)
│   ├── audio_service.py     # Whisper transcription
│   ├── models.py            # Pydantic request/response models
│   └── seed_data.py         # Sample data loader (Boston student)
├── frontend/
│   └── app.py               # Streamlit UI (tabs: Add, View, Monthly, BI Dashboard)
├── database/
│   └── expenses.db          # Created at runtime (gitignored)
├── telegram_bot.py          # Telegram bot (forwards messages to API)
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **Ollama not responding** | Run `ollama serve`. Ensure `ollama pull llama3.1` has been run. |
| **“Could not reach API” in app** | Start the backend (Process 1). In sidebar set **Backend API URL** to `http://127.0.0.1:8000` (or your backend URL). |
| **Port 8000 or 8501 in use** | Stop the process using that port, or use different ports: `uvicorn main:app --port 8001`, `streamlit run app.py --server.port 8502`. Update **Backend API URL** if you change the backend port. |
| **Whisper errors** | First voice request downloads the Whisper model (~75MB for “tiny”). Use Python 3.12 if you see compatibility errors. |
| **Telegram bot not replying** | Ensure backend is running and `EXPENSE_API_URL` is correct. Check that `TELEGRAM_BOT_TOKEN` is set and valid. |
| **Telegram "OCR not available"** | Install: `pip install easyocr`. The bot will still add expenses from text and answer report requests. |
| **Add expense fails (500)** | Check backend logs. Often Ollama is not running or llama3.1 is not pulled. |

---

## Summary: order of operations

1. **One-time:** Install Python 3.10+, create venv, `pip install -r requirements.txt`, install Ollama and `ollama pull llama3.1`.
2. **Each session:** Start **backend** (Process 1), then **frontend** (Process 2). Optionally run **Telegram bot** (Process 4) and/or load **sample data** (Process 3).
3. **Use:** Add expenses via web (text/voice) or Telegram; view in **View Expenses**; run **Monthly Summary** and **BI Dashboard**; export or embed for Power BI as needed.


Note 

8315431091:AAGV7l5siVKpx6htWSIH9AuMpvHI3aF1DL4 BOT - ID