# Setup & run guide

This document explains **what you need** and **how to run** SelavAI (Personal Financial Assistant).

**→ For features and functionality,** see **[README.md](README.md)**.

---

## What you need

### Required

- **Python 3.10+** (3.12 recommended)
- **Node.js 18+** (only if you use the React frontend; npm comes with Node)

### For AI features (text/voice extraction, summaries, chat)

- **Ollama** — [Install from ollama.ai](https://ollama.ai), then:
  ```bash
  ollama pull llama3.1
  ollama serve   # keep this running when using AI features
  ```

### Optional

- **Voice input (Chat)** — Requires `openai-whisper`. On Python 3.12+, the install may fail; see [If pip install fails](#if-pip-install-fails) below.
- **Document upload (PDF/images in Chat)** — Requires **EasyOCR** (images) and **PyMuPDF** (PDFs). Both are in `requirements.txt`.
- **Telegram** — Create a bot with [@BotFather](https://t.me/BotFather), get a token, and set `TELEGRAM_BOT_TOKEN`.
- **Gmail** — To sync expenses from Gmail: Google Cloud project with Gmail API enabled, OAuth credentials, and one-time auth (see [Gmail sync](#optional-gmail-sync) below).
- **Finance News** — Set `TAVILY_API_KEY` (from [tavily.com](https://tavily.com)) to enable the Finance News tab.
- **Wealth Hub — real-time stock prices** — Install `yfinance` (`pip install yfinance`) and set `STOCK_PROVIDER=yfinance`. Portfolio and watchlist prices will be fetched from Yahoo Finance on each request (delayed data; no API key required).
- **Docker** — To run the app with Docker Compose (backend + frontend in containers).

---

## One-time setup

From the **project root** (`financial_app/`):

### 1. Virtual environment and Python dependencies

```bash
python3 -m venv venv
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

First install can take a few minutes (e.g. PyTorch, Whisper, EasyOCR, PyMuPDF).

#### If pip install fails

**`openai-whisper` fails with `ModuleNotFoundError: No module named 'pkg_resources'`** (common on Python 3.12+):

```bash
pip install setuptools==81.0.0
pip install openai-whisper --no-build-isolation
pip install -r requirements.txt
```

The app runs without Whisper; only **voice input** in Chat is disabled until the above is run.

**`torch==2.1.0` not found** — The project uses `torch>=2.2.0`; if you already installed Whisper, it may have pulled a newer torch. Run `pip install -r requirements.txt` again after the Whisper workaround.

### 2. (Optional) React frontend dependencies

If you will use the React UI:

```bash
cd frontend-react
npm install
cd ..
```

You can skip this if you use the **single script** or **Docker**; the script runs `npm install` when needed, and Docker builds the frontend image.

---

## How to run the application

### Option 1: Single script (easiest — macOS / Linux)

From the project root:

```bash
source venv/bin/activate   # if not already
./run_all.sh
```

- **Backend:** http://127.0.0.1:8000  
- **React frontend:** http://localhost:5173  

Open http://localhost:5173 and:

- **Default login** — Click **“Default login (demo account)”** to try the app with pre-filled demo user and sample data (no sign-up).
- **Sign up** — Create an account with username, password, and optional salary/budget/currency.
- **Sign in** — Use your credentials.

Press **Ctrl+C** to stop both backend and frontend.

**Streamlit instead of React:**

```bash
./run_all.sh streamlit
```

- React → http://localhost:5173  
- Streamlit → http://localhost:8501  

**With Telegram bot:** set the token before running (or add it to `.env`; the script loads `.env` if present):

```bash
export TELEGRAM_BOT_TOKEN=your_token_from_botfather
./run_all.sh
# Or: copy .env.example to .env, add your token, then ./run_all.sh
```

### Option 2: Windows (PowerShell)

From the project root:

```powershell
.\run_all.ps1
```

- Backend: http://127.0.0.1:8000  
- React UI: http://localhost:5173  

With Telegram:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your_token"
.\run_all.ps1
```

### Option 3: Docker

From the project root:

```bash
docker compose up -d
```

- **UI:** http://localhost:8080  
- **API:** http://localhost:8000 (docs: http://localhost:8000/docs)  
- Data is stored in a Docker volume (`expense_data`).

With Telegram bot:

```bash
export TELEGRAM_BOT_TOKEN=your_token
docker compose --profile bot up -d
```

Rebuild after code changes:

```bash
docker compose up -d --build
```

**Note:** AI features (Ollama) usually run on the host. The backend in Docker may need to be configured to use the host (e.g. `host.docker.internal` on Docker Desktop) to reach Ollama.

### Option 4: Manual (separate terminals)

**Terminal 1 — Backend**

From project root, with venv activated:

```bash
export PYTHONPATH="${PWD}/backend:${PWD}:${PYTHONPATH}"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000  
- API docs: http://127.0.0.1:8000/docs  

**Terminal 2 — Frontend (React)**

```bash
cd frontend-react
npm install
npm run dev
```

Open http://localhost:5173. In the app, **Settings → Backend API URL** = `http://127.0.0.1:8000` if needed.

**Streamlit:**

```bash
cd frontend
streamlit run app.py --server.port 8501
```

Open http://localhost:8501. Set **Backend API URL** in the sidebar if needed.

---

## Login & accounts

- **Default login (demo)** — On the login page, click **“Default login (demo account)”**. Uses username `demo`, password `demo`. On first use, sample expenses/limits/goals are loaded for that user. No sign-up required.
- **Register** — Create an account with username, password, and optional salary, monthly budget, and currency. All data is scoped to your user.
- **Log out** — Settings → Log out. Your data remains; next time sign in with the same account.

If the backend was just updated or restarted and Default login shows **“Not Found”**, restart the backend (e.g. run `./run_all.sh` again) so the auth routes are loaded.

---

## Optional: Telegram bot (standalone)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. With the **backend already running** (same machine or reachable URL):

   ```bash
   source venv/bin/activate
   export TELEGRAM_BOT_TOKEN=your_token
   export EXPENSE_API_URL=http://127.0.0.1:8000
   python telegram_bot.py
   ```

3. In Telegram: send **text** to add expenses, **photo** for receipt OCR (needs EasyOCR), or **"report"** / **"report February 2025"** for a monthly summary.

---

## Optional: Gmail sync

1. **Google Cloud:** Create a project → enable **Gmail API** → create **OAuth 2.0 Client ID** (Desktop app) → download JSON.
2. Save the JSON as `backend/credentials.json` (or set `GMAIL_CREDENTIALS_JSON` to its path).
3. **One-time auth:**

   ```bash
   python backend/gmail_auth.py
   ```

   Log in in the browser; this creates `backend/token.json`. Do not commit `credentials.json` or `token.json`.

4. In the app: **Settings → Gmail** — check status and click **Sync Gmail** (or say **“Sync Gmail”** in Chat).

---

## Optional: Sample data

- **From the app:** In **Chat**, say **“Add sample data”** (or use the quick-action chip). Or go to **Settings** and click **Add sample data**. Data is added for the **current user**.
- **From the command line** (for the default/local user):

  ```bash
  source venv/bin/activate
  python -c "
  from backend import database, seed_data
  database.init_database()
  seed_data.load_sample_data(user_id='local')
  print('Sample data loaded.')
  "
  ```

---

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `EXPENSE_API_URL` | Frontend, Telegram bot | Backend URL (e.g. `http://127.0.0.1:8000`). Default in app: `http://127.0.0.1:8000`. |
| `VITE_EXPENSE_API_URL` | React build | Backend URL at build time (optional). |
| `TELEGRAM_BOT_TOKEN` | `telegram_bot.py` | Token from @BotFather. Required to run the bot. |
| `GMAIL_CREDENTIALS_JSON` | Backend Gmail | Path to OAuth client JSON (default: `backend/credentials.json`). |
| `GMAIL_TOKEN_JSON` | Backend Gmail | Path to saved token (default: `backend/token.json`). |
| `EXPENSE_DEFAULT_USER_ID` | Backend | Default user id when no auth (default: `local`). |
| `TAVILY_API_KEY` | Backend (Finance News) | API key from [tavily.com](https://tavily.com). Enables the **Finance News** tab. |
| `STOCK_PROVIDER` | Backend (Wealth Hub) | Set to `yfinance` or `yahoo` to fetch live/delayed stock prices from Yahoo Finance (requires `pip install yfinance`). Omit for static mock prices. |

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **“Could not reach API” in app** | Start the backend first. Set **Backend API URL** in **Settings** (React) to `http://127.0.0.1:8000`. |
| **Default login shows “Not Found”** | Restart the backend so auth routes load. Ensure you’re not pointing the app at a different server (e.g. wrong API URL). |
| **“table users has no column named username”** | Database was created before auth was added. Delete or rename `database/expenses.db` and restart the backend to recreate the schema (you will lose local data). |
| **Ollama not responding** | Run `ollama serve` and ensure `ollama pull llama3.1` has been run. |
| **Port 8000 or 5173 in use** | Stop the process on that port or use another port. Update Backend API URL if you change the backend port. |
| **Backend fails: “No module named 'llm_service'”** | Run with `PYTHONPATH` set. The `run_all.sh` script does this. Manually: `export PYTHONPATH="${PWD}/backend:${PWD}"` before uvicorn. |
| **Telegram bot not replying** | Ensure backend is running and `EXPENSE_API_URL` is correct. Check `TELEGRAM_BOT_TOKEN` is set and valid. |
| **Add expense / Chat returns 500** | Check backend logs. Often Ollama is not running or `llama3.1` is not pulled. |
| **Voice (Whisper) errors** | Install with the [Whisper workaround](#if-pip-install-fails) above. First voice use downloads the model. |
| **Document upload: “No text could be extracted”** | For images: ensure EasyOCR is installed (`pip install easyocr`). For PDFs: ensure PyMuPDF is installed (`pip install pymupdf`). |
| **Finance News: “TAVILY_API_KEY not set”** | Add `TAVILY_API_KEY=tvly-...` to `.env` (get a key at tavily.com) and restart the backend. |

---

## Quick reference

- **README.md** — [Features and functionality](README.md)
- **SETUP.md** — This file (setup and run)
- **API docs** — http://127.0.0.1:8000/docs (when backend is running)
