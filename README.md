# SelavAI — Personal Financial Assistant

**SelavAI** is a voice-enabled personal financial assistant with local AI. Add expenses via **text**, **voice**, or **PDF/images** in the web app; ask questions about your spending; and control **limits**, **goals**, **forecast**, and more through a single **Chat** assistant. All data is stored locally (SQLite); extraction and insights use your local **Ollama** LLM.

**→ How to run:** see **[SETUP.md](SETUP.md)** for prerequisites, installation, and run options (single script, Docker, or manual).

---

## Features & functionality

### Chat assistant (one place for almost everything)

The **Chat** tab is a flexible assistant that can:

| You say | What happens |
|--------|----------------|
| **"$50 on groceries yesterday"** | Adds the expense (date, category, amount extracted by AI). |
| **"Summary for last week"** / **"Last two days"** | Returns spending total and optional breakdown by category. |
| **"Break it down by category"** | Same period, formatted by category. |
| **"Set food limit to 500"** / **"Show my limits"** | Sets or lists monthly category limits. |
| **"My goals"** / **"Add goal save 5000 by 2026"** | Lists or creates financial goals. |
| **"Can I afford 100 for dinner?"** | Affordability check (limits, forecast, goals). |
| **"Forecast"** / **"Alerts"** | Projected month-end spending and limit alerts. |
| **"Sync Gmail"** / **"Add sample data"** | Syncs Gmail expenses or loads demo data (expenses, limits, goals, and Wealth Hub: salary, investments, watchlist, liability). |
| **"Help"** | Lists everything the assistant can do. |

You can also **upload PDFs or images** (receipts) in Chat; the app uses **OCR** (images) and **PDF text extraction** to pull out expenses and add them. Conversation history is sent so follow-ups (e.g. “By category”) work in context.

### Adding expenses

| Feature | What it does |
|--------|----------------|
| **Text (Chat)** | Type a sentence (e.g. “Spent $45 on groceries yesterday”). The AI extracts date, category, amount, and currency and saves the expense. |
| **Voice (Chat)** | Record audio; Whisper transcribes it and the same pipeline extracts and saves the expense. |
| **PDF / images (Chat)** | Upload receipts or documents. OCR (EasyOCR) and PDF text (PyMuPDF) extract text; the LLM extracts expense lines and saves them. |
| **Telegram bot** | Send text (e.g. “50 dollars lunch today”) or a photo of a receipt; the bot adds the expense and can reply with a monthly report. |
| **Gmail sync** | Connect Gmail (one-time OAuth, in **Settings**). The app fetches emails matching a search (e.g. receipts, payments), extracts expenses via the same AI, and saves them. |

### Viewing & analyzing

| Feature | What it does |
|--------|----------------|
| **Expenses** | List all expenses with date, category, amount, and notes. Filter and manage. |
| **Monthly summary** | Pick a year and month; the AI generates a written summary and lists that month’s expenses. |
| **BI Dashboard** | Interactive charts: spending over time, by category, monthly totals. Set a date range, see KPIs and budget health, and **download CSV**. |
| **Insights** | Budget health score, KPIs, category breakdown, trends, forecast, recommendations, anomaly detection, and optional AI narrative. |
| **Recurring** | Detects recurring expenses (subscriptions, etc.) from your history. Recompute to refresh. |
| **Finance News** | Finance-related news (Tavily); optional, set `TAVILY_API_KEY`. |

### Limits & goals

| Feature | What it does |
|--------|----------------|
| **Limits & alerts** | Set monthly limits per category (or “total”). Near-limit and over-limit alerts in the app and (if enabled) in Telegram. |
| **Forecast & predictive alerts** | Projected month-end spending and categories on track to exceed limits. |
| **Goals** | Savings targets, spending reductions, or category caps. Track progress and suggested pace. |
| **Affordability check** | “Can I afford this?” using limits, projected spend, recurring, and goals. |
| **Scenario simulator** | “What if” changes (e.g. reduce category, add one-time expense) without changing real data. |

### Wealth Hub

| Feature | What it does |
|--------|----------------|
| **Overview** | Command center: summary strip (income, expenses, portfolio, net worth), priority alerts, “What should I do next?”, wealth flow, goal and net worth previews. |
| **Income (salary)** | Record salary/income by month; used for cashflow and net worth. |
| **Investments** | Log BUY/SELL/DIVIDEND transactions; portfolio is built from these. |
| **Portfolio** | Holdings, allocation by sector, latest transactions, dividend summary, unrealized P&L. Optional **real-time stock prices** (set `STOCK_PROVIDER=yfinance`; see SETUP.md). |
| **Cashflow** | Monthly income vs expenses, ratios, fixed/variable split, investable surplus, month-over-month. |
| **Projections** | Scenario comparison and projected guidance (6m, 1y, 3y). |
| **Portfolio Intelligence** | Diversification score, sector gaps, rebalancing suggestions. |
| **Suggestions** | Prioritized actions (expense ratio, emergency fund, etc.) with “why” and links. |
| **Goals** | Wealth-focused goals; preview on overview. |
| **Watchlist** | Track tickers and target buy prices. |
| **Net worth** | Assets (cash + portfolio) minus liabilities (e.g. loans). |

### Review & quality

| Feature | What it does |
|--------|----------------|
| **Review queue** | Low-confidence or unverified expenses; verify or correct date, category, amount, or delete. |
| **Ask / Chat** | Natural-language questions over your data (e.g. “How much did I spend on food last month?”). |

### Account & data

| Feature | What it does |
|--------|----------------|
| **Login / register** | Create an account with username/password; optionally set salary, monthly budget, and currency. |
| **Default login** | Try the app with a demo account (username/password: `demo` / `demo`) and sample data. |
| **Settings** | Account info, Backend API URL, Gmail sync, **Clear all data** (includes Wealth Hub), **Add sample data** (expenses, limits, goals, and Wealth Hub: salary, investments, watchlist, liability). |

---

## Tech stack

- **Backend:** FastAPI, SQLite, Ollama (LLM), Whisper (speech-to-text, optional)
- **Frontend:** React (Vite, TypeScript, Tailwind, Recharts) or Streamlit
- **Optional:** Telegram (python-telegram-bot), Gmail (Google APIs), EasyOCR (receipt images), PyMuPDF (PDF text), Tavily (finance news), yfinance (real-time stock prices in Wealth Hub)

---

## Documentation

- **[SETUP.md](SETUP.md)** — Prerequisites, one-time setup, how to run (script / Docker / manual), optional Telegram/Gmail/sample data, Wealth Hub real-time stocks (`STOCK_PROVIDER`), environment variables, and troubleshooting.
- **API docs** — When the backend is running: **http://127.0.0.1:8000/docs**

---

## Project structure

```
financial_app/
├── backend/              # FastAPI app, database, services
│   ├── main.py           # Routes (auth, expenses, limits, goals, chat, Gmail, admin, wealth, etc.)
│   ├── chat_service.py   # Unified chat (add expense / ask / actions)
│   ├── chat_actions.py   # Chat action layer (limits, goals, affordability, forecast, Gmail, help)
│   ├── document_service.py  # OCR + PDF text extraction for document uploads
│   ├── nl_query_service.py  # Natural language expense queries (last week, by category, etc.)
│   ├── extraction_service.py
│   ├── llm_service.py
│   ├── audio_service.py  # Whisper (voice)
│   ├── seed_data.py      # Sample data (expenses, limits, goals, Wealth Hub)
│   ├── wealth_*.py       # Wealth Hub: overview, portfolio, cashflow, projections, suggestions, net worth, stock (mock/live)
│   └── ...
├── frontend-react/       # React UI (Vite, Tailwind, Recharts)
├── frontend/             # Streamlit UI
├── database/             # SQLite DB (created at runtime)
├── telegram_bot.py       # Telegram bot
├── run_all.sh            # Run backend + frontend (macOS/Linux)
├── run_all.ps1           # Run backend + frontend (Windows)
├── requirements.txt
├── README.md             # This file
└── SETUP.md              # Setup and run instructions
```
