# AI Expense Tracker

A voice-enabled expense tracking application with local AI. Add expenses via **text or voice** in the web app, through **Telegram**, or by **syncing Gmail**. All data is stored locally (SQLite); extraction and insights use your local **Ollama** LLM.

**→ How to run the application:** see **[SETUP.md](SETUP.md)** for prerequisites, installation, and run options (single script, Docker, or manual).

---

## Features & functionality

### Adding expenses

| Feature | What it does |
|--------|----------------|
| **Text input** | Type a sentence (e.g. “Spent $45 on groceries yesterday”). The AI extracts date, category, amount, and currency and saves the expense. |
| **Voice input** | Record audio in the app. Whisper transcribes it; the same AI pipeline extracts and saves the expense. |
| **Telegram bot** | Send a text message (e.g. “50 dollars lunch today”) or a photo of a receipt; the bot adds the expense and can reply with a monthly report. |
| **Gmail sync** | Connect Gmail (one-time OAuth). The app fetches emails matching a search (e.g. receipts, payments), extracts expenses via the same AI, and saves them. |

### Viewing & analyzing

| Feature | What it does |
|--------|----------------|
| **View expenses** | List all expenses with date, category, amount, and notes. See totals and category counts. |
| **Monthly summary** | Pick a year and month; the AI generates a written summary and lists that month’s expenses. |
| **BI Dashboard** | Interactive charts: spending over time (area), spending by category (bar), share by category (donut), and monthly totals (bar). Set a date range, see KPIs and budget health, and **download CSV** for Power BI or Excel. |
| **Insights** | Budget health score, KPI cards (total spend, transactions, vs previous period, recurring burden), category breakdown, 6‑month trends, forecast, recommendations, anomaly detection, and an optional AI narrative. |
| **Recurring** | Detects recurring expenses (subscriptions, etc.) from your history. Recompute to refresh. |

### Limits & goals

| Feature | What it does |
|--------|----------------|
| **Limits & alerts** | Set monthly limits per category (or “total”). Get **near limit** (80%+) and **over limit** alerts in the app and (if enabled) in Telegram. |
| **Forecast & predictive alerts** | See projected month-end spending and which categories are on track to exceed limits. |
| **Goals** | Create savings targets, spending reductions, or category caps. Track progress, distance to goal, and suggested monthly/weekly pace. Edit and delete goals. |
| **Affordability check** | Enter an amount and category (and optional merchant). The app tells you if you can afford it based on limits, projected spend, recurring burden, and goals, with reasons and impact details. |
| **Scenario simulator** | Test “what if” changes (e.g. reduce category by %, remove a subscription, add a one-time expense, change a cap, save per week) without changing real data. Compare baseline vs simulated spending and see limit/goal impact. |

### Review & quality

| Feature | What it does |
|--------|----------------|
| **Review queue** | Low-confidence or unverified expenses appear here. Verify or correct date, category, amount, and currency, or delete. |
| **Ask AI** | Ask questions in natural language (e.g. “How much did I spend on food last month?”). The AI uses your expense data to answer; you can inspect parsed filters and supporting data. |

### Export & integration

| Feature | What it does |
|--------|----------------|
| **Download CSV** | From the BI Dashboard, export the filtered date range as CSV for Power BI, Tableau, or spreadsheets. |
| **API** | REST API for all operations (add expense, list expenses, limits, goals, affordability, simulate, insights, Gmail sync, etc.). Interactive docs at `/docs` when the backend is running. |

---

## Tech stack

- **Backend:** FastAPI, SQLite, Ollama (LLM), Whisper (speech-to-text)
- **Frontend:** React (Vite, TypeScript, Tailwind) or Streamlit
- **Optional:** Telegram (python-telegram-bot), Gmail (Google APIs), EasyOCR (receipt images)

---

## Documentation

- **[SETUP.md](SETUP.md)** — What you need to run the app, one-time setup, how to run (script / Docker / manual), optional Telegram/Gmail/sample data, environment variables, and troubleshooting.
- **API docs** — When the backend is running, open **http://127.0.0.1:8000/docs** for interactive API reference.

---

## Project structure

```
financial_app/
├── backend/           # FastAPI app, database, services (LLM, Whisper, extraction, insights, goals, etc.)
├── frontend/          # Streamlit UI
├── frontend-react/    # React UI (Vite, Tailwind, Recharts)
├── tests/             # Pytest tests
├── database/          # SQLite DB (created at runtime)
├── telegram_bot.py    # Telegram bot
├── run_all.sh         # Run backend + frontend (macOS/Linux)
├── run_all.ps1        # Run backend + frontend (Windows PowerShell)
├── requirements.txt
├── README.md          # This file — features & functionality
└── SETUP.md           # Setup and run instructions
```
