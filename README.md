# AI Expense Tracker

A voice-enabled expense tracking application with local LLM processing using Ollama.

## Features
- 🎤 Voice input with Whisper transcription
- ⌨️ Text input for quick entry
- 🤖 AI-powered expense extraction using llama3.1
- 📊 SQLite database storage
- 📈 Monthly analytics with AI insights
- 🌐 Public access via Cloudflare tunnels

## Prerequisites
- Python 3.10+
- Ollama installed and running
- llama3.1 model pulled

## Quick Start

### 1. Install Ollama
```bash
# Install Ollama from https://ollama.ai
# Pull the model
ollama pull llama3.1
```

### 2. Setup Project
```bash
# Clone/create project directory
mkdir expense-tracker
cd expense-tracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Locally
```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
streamlit run app.py --server.port 8501
```

Access at: http://localhost:8501

### 4. Public Access (Optional)

Install Cloudflared:
```bash
# Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

Expose services:
```bash
# Terminal 3: Expose backend
cloudflared tunnel --url http://localhost:8000

# Terminal 4: Expose frontend
cloudflared tunnel --url http://localhost:8501
```

Use the generated HTTPS URLs to access from anywhere!

## Usage

### Adding Expenses

**Text:**
- "Spent $45 on groceries yesterday"
- "Paid 2000 rupees for uber today"
- "Coffee for 5 euros this morning"

**Voice:**
- Click record button
- Say your expense
- Click stop and process

### Monthly Summary
1. Go to "Monthly Summary" tab
2. Select year and month
3. Click "Generate Summary"
4. View AI-generated insights

## Project Structure
```
expense-tracker/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLite operations
│   ├── llm_service.py       # Ollama integration
│   ├── audio_service.py     # Whisper integration
│   └── models.py            # Pydantic models
├── frontend/
│   └── app.py               # Streamlit UI
├── database/
│   └── expenses.db          # Auto-created
└── requirements.txt
```

## Troubleshooting

**Ollama not responding:**
```bash
ollama serve
```

**Whisper model download:**
First run will download Whisper model (tiny: ~75MB)

**Port already in use:**
Change ports in run commands:
```bash
uvicorn main:app --port 8001
streamlit run app.py --server.port 8502
```
