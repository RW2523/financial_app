#!/usr/bin/env bash
#
# Run the entire Expense Tracker app: backend API + React frontend (+ optional Telegram bot).
# Usage: ./run_all.sh [react|streamlit]
#   react     (default) React UI at http://localhost:5173
#   streamlit Streamlit UI at http://localhost:8501
#
# Backend API: http://127.0.0.1:8000
# Set TELEGRAM_BOT_TOKEN to also start the Telegram bot (optional).
#

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# So backend can resolve imports like "import llm_service" when run as backend.main
export PYTHONPATH="${ROOT}/backend:${ROOT}:${PYTHONPATH}"

# Optional: activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Optional: load .env so TELEGRAM_BOT_TOKEN can be set there
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

BACKEND_PID=""
BOT_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$BOT_PID" ]    && kill "$BOT_PID" 2>/dev/null || true
  exit 0
}

trap cleanup SIGINT SIGTERM

# Ensure database directory exists
mkdir -p database

# 1) Start backend
echo "Starting backend API on http://127.0.0.1:8000"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
  echo "Backend failed to start. Check dependencies: pip install -r requirements.txt"
  exit 1
fi

# 2) Optional Telegram bot
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Starting Telegram bot..."
  export EXPENSE_API_URL="${EXPENSE_API_URL:-http://127.0.0.1:8000}"
  python telegram_bot.py &
  BOT_PID=$!
  sleep 1
  if kill -0 "$BOT_PID" 2>/dev/null; then
    echo "Telegram bot running (EXPENSE_API_URL=$EXPENSE_API_URL)"
  else
    echo "Telegram bot failed to start (check token and: pip install python-telegram-bot aiohttp)"
    BOT_PID=""
  fi
else
  echo "Telegram bot skipped (set TELEGRAM_BOT_TOKEN or add to .env to enable)"
fi

# 3) Frontend (foreground so Ctrl+C triggers cleanup)
UI="${1:-react}"
if [ "$UI" = "streamlit" ]; then
  echo "Starting Streamlit UI at http://localhost:8501"
  (cd frontend && streamlit run app.py --server.port 8501)
else
  echo "Starting React UI at http://localhost:5173"
  if [ ! -d "frontend-react/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd frontend-react && npm install)
  fi
  (cd frontend-react && npm run dev)
fi
