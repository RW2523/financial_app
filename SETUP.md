# Setup & run guide

This document explains **what you need** and **how to run** the AI Expense Tracker.

**→ For features and functionality,** see **[README.md](README.md)**.

---

## What you need

### Required

- **Python 3.10+** (3.12 recommended)
- **Node.js 18+** (only if you use the React frontend; npm comes with Node)

### For AI features (text/voice extraction, summaries)

- **Ollama** — [Install from ollama.ai](https://ollama.ai), then:
  ```bash
  ollama pull llama3.1
  ollama serve   # keep this running if you use AI features
  ```

### Optional

- **Telegram** — To use the Telegram bot: create a bot with [@BotFather](https://t.me/BotFather), get a token, and set `TELEGRAM_BOT_TOKEN`.
- **Gmail** — To sync expenses from Gmail: Google Cloud project with Gmail API enabled, OAuth credentials, and one-time auth (see [Gmail sync](#gmail-sync-optional) below).
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

First install can take a few minutes (e.g. PyTorch, Whisper).

### 2. (Optional) React frontend dependencies

If you will use the React UI:

```bash
cd frontend-react
npm install
cd ..
```

You can skip this if you only use the **single script** or **Docker**; the script runs `npm install` when needed, and Docker builds the frontend image.

---

## How to run the application

Pick one of the options below.

### Option 1: Single script (easiest — macOS / Linux)

From the project root:

```bash
source venv/bin/activate   # if not already
./run_all.sh
```

- Starts the **backend** at **http://127.0.0.1:8000**
- Starts the **React frontend** at **http://localhost:5173**
- Press **Ctrl+C** to stop both

**Streamlit instead of React:**

```bash
./run_all.sh streamlit
```

- React UI → **http://localhost:5173**
- Streamlit UI → **http://localhost:8501**

**With Telegram bot:** set the token before running, or add it to a `.env` file (the script loads `.env` if present):

```bash
export TELEGRAM_BOT_TOKEN=your_token_from_botfather
./run_all.sh
# Or: copy .env.example to .env, add your token, then ./run_all.sh
```

### Option 2: Single script on Windows (PowerShell)

From the project root:

```powershell
.\run_all.ps1
```

- Backend: **http://127.0.0.1:8000**
- React UI: **http://localhost:5173**

With Telegram bot:

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

**With Telegram bot:**

```bash
export TELEGRAM_BOT_TOKEN=your_token
docker compose --profile bot up -d
```

**Rebuild after code changes:**

```bash
docker compose up -d --build
```

**Note:** AI features (Ollama) usually run on the host. The backend in Docker cannot reach `localhost` on the host by default; for Docker + Ollama you may need to configure the backend to use the host (e.g. `host.docker.internal` on Docker Desktop).

### Option 4: Manual (separate terminals)

Use this if you prefer to run backend and frontend yourself.

**Terminal 1 — Backend**

From project root, with venv activated:

```bash
export PYTHONPATH="${PWD}/backend:${PWD}:${PYTHONPATH}"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

- API: **http://127.0.0.1:8000**
- API docs: **http://127.0.0.1:8000/docs**

**Terminal 2 — Frontend**

**React:**

```bash
cd frontend-react
npm install
npm run dev
```

- Open **http://localhost:5173**
- In the app: **Settings → Backend API URL** = `http://127.0.0.1:8000` if needed

**Streamlit:**

```bash
cd frontend
streamlit run app.py --server.port 8501
```

- Open **http://localhost:8501**
- In the sidebar: **Backend API URL** = `http://127.0.0.1:8000` if needed

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

3. In Telegram: send **text** to add expenses, **photo** for receipt OCR (needs `pip install easyocr`), or **"report"** / **"report February 2025"** for a monthly summary.

---

## Optional: Gmail sync

1. **Google Cloud:** Create a project → enable **Gmail API** → create **OAuth 2.0 Client ID** (Desktop app) → download JSON.
2. Save the JSON as `backend/credentials.json` (or set `GMAIL_CREDENTIALS_JSON` to its path).
3. **One-time auth:**

   ```bash
   python backend/gmail_auth.py
   ```

   Log in in the browser; this creates `backend/token.json`. Do not commit `credentials.json` or `token.json`.

4. In the app, open **Gmail** (or Gmail Sync), adjust the search query if needed, and click **Sync Gmail**.

---

## Optional: Sample data

To pre-fill the database with sample expenses:

```bash
source venv/bin/activate
python backend/seed_data.py
```

Then open **View** or **BI Dashboard** in the app and refresh.

---

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `EXPENSE_API_URL` | Frontend, Telegram bot | Backend URL (e.g. `http://127.0.0.1:8000`). Default in app: `http://127.0.0.1:8000`. |
| `TELEGRAM_BOT_TOKEN` | `telegram_bot.py` | Token from @BotFather. Required to run the bot. |
| `GMAIL_CREDENTIALS_JSON` | Backend Gmail | Path to OAuth client JSON (default: `backend/credentials.json`). |
| `GMAIL_TOKEN_JSON` | Backend Gmail | Path to saved token (default: `backend/token.json`). |
| `EXPENSE_DEFAULT_USER_ID` | Backend | Default user id for data (default: `local`). |
| `TAVILY_API_KEY` | Backend (Finance News) | API key from [tavily.com](https://tavily.com). Enables the **Finance News** tab. |

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **“Could not reach API” in app** | Start the backend first. Set **Backend API URL** in the app (Settings in React, sidebar in Streamlit) to `http://127.0.0.1:8000`. |
| **Ollama not responding** | Run `ollama serve` and ensure `ollama pull llama3.1` has been run. |
| **Port 8000 or 5173 in use** | Stop the process on that port or use another port (e.g. `--port 8001` for uvicorn). Update Backend API URL if you change the backend port. |
| **Backend fails: “No module named 'llm_service'”** | Run with `PYTHONPATH` set (the `run_all.sh` script does this). Manually: `export PYTHONPATH="${PWD}/backend:${PWD}"` before uvicorn. |
| **Telegram bot not replying** | Ensure backend is running and `EXPENSE_API_URL` is correct. Check `TELEGRAM_BOT_TOKEN` is set and valid. |
| **Add expense returns 500** | Check backend logs. Often Ollama is not running or `llama3.1` is not pulled. |
| **Whisper errors (voice)** | First voice use downloads the Whisper model. Use Python 3.12 if you see compatibility errors. |
| **Finance News shows “TAVILY_API_KEY not set”** | Add `TAVILY_API_KEY=tvly-...` to `.env` (get a key at tavily.com) and restart the backend. |

---

## Quick reference

- **README.md** — [Features and functionality](README.md)
- **SETUP.md** — This file (setup and run)
- **API docs** — http://127.0.0.1:8000/docs (when backend is running)
