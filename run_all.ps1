# Run the entire Expense Tracker app (Windows PowerShell)
# Backend + React frontend. Optional: set $env:TELEGRAM_BOT_TOKEN to start the bot.
# Usage: .\run_all.ps1 [react|streamlit]

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

# Activate venv if present
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

# Ensure database dir exists
New-Item -ItemType Directory -Force -Path database | Out-Null

# Start backend in background
Write-Host "Starting backend API on http://127.0.0.1:8000"
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:Root
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
}
Start-Sleep -Seconds 2
if ($backendJob.State -ne "Running") {
    Receive-Job $backendJob
    Write-Host "Backend failed to start. Run: pip install -r requirements.txt"
    exit 1
}

# Optional Telegram bot
if ($env:TELEGRAM_BOT_TOKEN) {
    Write-Host "Starting Telegram bot..."
    if (-not $env:EXPENSE_API_URL) { $env:EXPENSE_API_URL = "http://127.0.0.1:8000" }
    $botJob = Start-Job -ScriptBlock {
        Set-Location $using:Root
        python telegram_bot.py
    }
}

# Frontend
$ui = if ($args[0]) { $args[0] } else { "react" }
if ($ui -eq "streamlit") {
    Write-Host "Starting Streamlit UI at http://localhost:8501"
    Set-Location frontend
    try { streamlit run app.py --server.port 8501 }
    finally { Stop-Job $backendJob -ErrorAction SilentlyContinue; Remove-Job $backendJob -ErrorAction SilentlyContinue }
} else {
    Write-Host "Starting React UI at http://localhost:5173"
    if (-not (Test-Path "frontend-react\node_modules")) {
        Write-Host "Installing frontend dependencies..."
        Set-Location frontend-react
        npm install
        Set-Location $Root
    }
    Set-Location frontend-react
    try { npm run dev }
    finally {
        Stop-Job $backendJob -ErrorAction SilentlyContinue
        Remove-Job $backendJob -ErrorAction SilentlyContinue
        if ($botJob) { Stop-Job $botJob -ErrorAction SilentlyContinue; Remove-Job $botJob -ErrorAction SilentlyContinue }
    }
}
