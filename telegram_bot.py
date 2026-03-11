#!/usr/bin/env python3
"""
Telegram bot: add expenses by text, by receipt/screenshot (OCR), or ask for a report.

- Text: send a message like "50 dollars on groceries yesterday" → saved via LLM.
- Photo: send a receipt/screenshot → OCR extracts text → LLM extracts expense → saved.
- Report: send "report", "summary", "report February", "report feb 2025" → reply with monthly summary.

Setup:
  1. Create a bot with @BotFather on Telegram → get token
  2. Set env: TELEGRAM_BOT_TOKEN=your_token, EXPENSE_API_URL=http://127.0.0.1:8000
  3. Run: python telegram_bot.py
"""
import asyncio
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from calendar import month_name

# Backend API (same machine or remote)
API_URL = os.environ.get("EXPENSE_API_URL", "http://127.0.0.1:8000").rstrip("/")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

try:
    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters
except ImportError:
    print("Install: pip install python-telegram-bot")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("Install: pip install aiohttp")
    sys.exit(1)

# Optional OCR (easyocr); bot still works without it for text and report
OCR_AVAILABLE = False
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    pass

# Month name to number
MONTH_NAMES = {m.lower(): i for i, m in enumerate(month_name) if m}
MONTH_ABBREV = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def run_ocr(image_path: str, lang: list = None) -> str:
    """Run OCR on image file. Returns extracted text. Sync, run in executor."""
    if not OCR_AVAILABLE:
        return ""
    try:
        reader = easyocr.Reader(lang or ["en"], gpu=False, verbose=False)
        result = reader.readtext(image_path, detail=0)
        return " ".join(result).strip() if result else ""
    except Exception as e:
        logger.exception("OCR error: %s", e)
        return ""


async def call_add_expense(text: str):
    """POST text to backend /add-text-expense. Returns (success, message)."""
    url = f"{API_URL}/add-text-expense"
    payload = {"text": text}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw = (data.get("raw_text") or "")[:70]
                    if len(data.get("raw_text") or "") > 70:
                        raw += "..."
                    msg = (
                        f"✅ Added\n"
                        f"  {data.get('date', '')} | {data.get('category', '')} | "
                        f"{data.get('currency', '')} {data.get('amount', 0):.2f}\n"
                        f"  \"{raw}\"\n"
                        f"  Recorded at: {_now_str()}"
                    )
                    return True, msg.strip()
                body = await resp.text()
                return False, f"API error {resp.status}: {body[:200]}"
    except asyncio.TimeoutError:
        return False, "Request timed out (LLM may be slow). Try again."
    except Exception as e:
        logger.exception("call_add_expense")
        return False, f"Error: {str(e)}"


async def call_monthly_summary(year: int, month: int):
    """POST to /monthly-summary. Returns (success, message or data)."""
    url = f"{API_URL}/monthly-summary"
    payload = {"year": year, "month": month}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return True, data
                body = await resp.text()
                return False, f"API error {resp.status}: {body[:200]}"
    except asyncio.TimeoutError:
        return False, "Request timed out."
    except Exception as e:
        logger.exception("call_monthly_summary")
        return False, str(e)


async def call_get_expenses():
    """GET /expenses. Returns (success, list or error message)."""
    url = f"{API_URL}/expenses"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return True, data
                return False, f"API error {resp.status}"
    except Exception as e:
        logger.exception("call_get_expenses")
        return False, str(e)


async def call_limits_status():
    """GET /limits/status. Returns (success, list of alert dicts or empty list)."""
    url = f"{API_URL}/limits/status"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return True, data.get("alerts", [])
                return False, []
    except Exception:
        return False, []


async def call_limits_status_full():
    """GET /limits/status. Returns (success, full dict with limits, spending, alerts)."""
    url = f"{API_URL}/limits/status"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return True, await resp.json()
                return False, None
    except Exception:
        return False, None


def format_limit_alerts(alerts: list) -> str:
    """Format limit alerts for Telegram reply."""
    if not alerts:
        return ""
    lines = ["\n⚠️ Limit alerts:"]
    for a in alerts:
        t = a.get("alert_type", "")
        cat = a.get("category", "")
        spent = a.get("spent", 0)
        limit = a.get("limit", 0)
        pct = a.get("percent", 0)
        if t == "over":
            lines.append(f"  🔴 {cat}: ${spent:.2f} / ${limit:.2f} ({pct}%) — over limit")
        else:
            lines.append(f"  🟡 {cat}: ${spent:.2f} / ${limit:.2f} ({pct}%) — near limit")
    return "\n".join(lines)


def detect_afford_intent(text: str) -> bool:
    """True if user is asking whether they can afford / should spend."""
    t = text.strip().lower()
    if len(t) < 10:
        return False
    patterns = [
        r"can i (go|get|have|spend|afford)",
        r"should i (go|buy|spend|get)",
        r"is it (ok|fine) (to|if i) (spend|go)",
        r"(do i |have i )?(got|have) (enough|room)",
        r"can i afford",
        r"will i be (over|ok) (if i )?spend",
        r"would (i be|that) (put me )?(over|within)",
        r"can (i |we )?(go for|have) (lunch|dinner|coffee)",
    ]
    return any(re.search(p, t) for p in patterns)


def parse_afford_query(text: str):
    """Extract (amount, category) from 'can I go for lunch that might take 50 dollars'. Returns (float or None, str or None)."""
    t = text.strip().lower()
    amount = None
    # $50 or 50 dollars or 50 bucks or like 50
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(?:dollars?|bucks?|usd)?", t, re.I)
    if m:
        amount = float(m.group(1))
    if amount is None:
        m = re.search(r"(?:like|about|around)\s+(\d+(?:\.\d+)?)", t)
        if m:
            amount = float(m.group(1))
    # Category hints
    category = None
    if re.search(r"lunch|dinner|breakfast|food|meal|coffee|eat|restaurant", t):
        category = "food"
    elif re.search(r"uber|taxi|transport|gas|petrol", t):
        category = "transport"
    elif re.search(r"movie|concert|entertainment", t):
        category = "entertainment"
    elif re.search(r"shopping|buy|store", t):
        category = "shopping"
    return amount, category


def format_afford_reply(amount: float, category: str, status: dict) -> str:
    """Build reply for 'can I spend X?' using limits and current spending."""
    spending = status.get("spending", {})
    limits = {lim["category"]: float(lim["amount"]) for lim in status.get("limits", [])}
    if not limits:
        return (
            f"You don't have any limits set, so I can't check. "
            f"This month you've spent ${spending.get('total', 0):.2f} total. "
            f"Set limits in the app (Limits & Alerts tab) to get a proper check."
        )
    lines = []
    # Check total
    total_spent = spending.get("total", 0)
    total_limit = limits.get("total")
    if total_limit is not None:
        after = total_spent + amount
        pct = (after / total_limit) * 100 if total_limit else 0
        if after > total_limit:
            over = after - total_limit
            lines.append(f"⚠️ Total: Adding ${amount:.2f} would put you at ${after:.2f} (over by ${over:.2f} of ${total_limit:.2f} limit).")
        elif pct >= 80:
            lines.append(f"🟡 Total: You'd be at ${after:.2f} / ${total_limit:.2f} ({pct:.0f}%) — close to your limit.")
        else:
            lines.append(f"✅ Total: ${after:.2f} / ${total_limit:.2f} ({pct:.0f}%) — within limit.")
    # Check category if we have one and a limit for it
    if category and category in limits:
        cat_spent = spending.get(category, 0)
        cat_limit = limits[category]
        after_cat = cat_spent + amount
        pct_cat = (after_cat / cat_limit) * 100 if cat_limit else 0
        if after_cat > cat_limit:
            over = after_cat - cat_limit
            lines.append(f"⚠️ {category}: Over by ${over:.2f} (${after_cat:.2f} / ${cat_limit:.2f}).")
        elif pct_cat >= 80:
            lines.append(f"🟡 {category}: ${after_cat:.2f} / ${cat_limit:.2f} ({pct_cat:.0f}%) — getting close.")
        else:
            lines.append(f"✅ {category}: ${after_cat:.2f} / ${cat_limit:.2f} — ok.")
    if not lines:
        lines.append(f"This month you've spent ${total_spent:.2f}. No limit would be exceeded by ${amount:.2f}.")
    return "\n".join(lines)


def parse_report_intent(text: str) -> tuple:
    """
    Parse 'report', 'summary', 'report feb', 'report february 2025', 'report 2 2025'.
    Returns (year, month) or (None, None) if not a report request.
    """
    t = text.strip().lower()
    if not t or t in ("report", "summary", "monthly report", "monthly summary", "report this month"):
        now = datetime.now()
        return now.year, now.month

    # "report february", "report feb", "report 2"
    m = re.match(r"(?:report|summary)\s+(.+)$", t)
    if not m:
        return None, None
    rest = m.group(1).strip()

    # "february 2025", "feb 2025", "2 2025", "2025-02"
    year = datetime.now().year
    month = None

    # 2025-02 or 2025/02
    dm = re.match(r"(\d{4})[-/](\d{1,2})", rest)
    if dm:
        year, month = int(dm.group(1)), int(dm.group(2))
        if 1 <= month <= 12:
            return year, month
        return None, None

    # "february 2025" or "feb 2025"
    parts = rest.split()
    for p in parts:
        if p.isdigit():
            y = int(p)
            if 2000 <= y <= 2100:
                year = y
            elif 1 <= y <= 12:
                month = y
        elif p in MONTH_ABBREV:
            month = MONTH_ABBREV[p]
        elif p in MONTH_NAMES:
            month = MONTH_NAMES[p]
    if month is None and rest.isdigit() and 1 <= int(rest) <= 12:
        month = int(rest)
    if month is not None and 1 <= month <= 12:
        return year, month
    return None, None


def format_report(data: dict) -> str:
    """Turn monthly-summary response into a short message."""
    year = data.get("year", "")
    month = data.get("month", "")
    total_expenses = data.get("total_expenses", 0)
    summary = (data.get("summary") or "").strip()
    expenses = data.get("expenses") or []
    total_amount = sum(float(e.get("amount", 0)) for e in expenses)
    by_cat = {}
    for e in expenses:
        c = e.get("category", "other")
        by_cat[c] = by_cat.get(c, 0) + float(e.get("amount", 0))
    top = sorted(by_cat.items(), key=lambda x: -x[1])[:5]
    lines = [
        f"📅 Report {year}-{month:02d}",
        f"  Transactions: {total_expenses}",
        f"  Total: ${total_amount:,.2f}",
        "",
        "Top categories:",
    ]
    for cat, amt in top:
        lines.append(f"  • {cat}: ${amt:,.2f}")
    if summary:
        lines.append("")
        lines.append("AI summary:")
        lines.append(summary[:800] + ("..." if len(summary) > 800 else ""))
    return "\n".join(lines)


def _now_str():
    """Current date and time for replies (ISO-style, 24h)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        f"🕐 _{_now_str()}_\n\n"
        "Send me:\n\n"
        "📝 *Text* – expense in plain language\n"
        "  e.g. 50 dollars on groceries yesterday\n\n"
        "🖼 *Photo* – receipt or screenshot\n"
        "  I’ll OCR it and add the expense (needs easyocr installed).\n\n"
        "📊 *Report* – ask for a summary\n"
        "  e.g. report, summary, report February, report feb 2025\n\n"
        "💰 *Can I afford?* – check before you spend\n"
        "  e.g. can I go for lunch that might take 50 dollars?\n\n"
        "Backend must be running; Ollama needed for adding expenses and AI summary."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with current date and time."""
    await update.message.reply_text(f"🕐 {_now_str()}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download photo, OCR, then add expense from extracted text. Always reply."""
    try:
        if not OCR_AVAILABLE:
            await update.message.reply_text(
                "OCR not available. Install: pip install easyocr\n"
                "You can still add expenses by sending text or use the web app for voice."
            )
            return
        await update.message.reply_chat_action("typing")
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        path = tempfile.mktemp(suffix=".jpg")
        await file.download_to_drive(path)
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, run_ocr, path)
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
        if not (text and len(text.strip()) > 5):
            await update.message.reply_text("Could not read enough text from the image. Try a clearer photo or add the expense in text.")
            return
        await update.message.reply_text(f"📷 Extracted text ({len(text)} chars). Adding expense…")
        ok, msg = await call_add_expense(text)
        if ok:
            ok_status, alerts = await call_limits_status()
            if ok_status and alerts:
                msg += format_limit_alerts(alerts)
        await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("handle_photo: %s", e)
        await update.message.reply_text(f"Something went wrong: {e}. Try again or send the expense as text.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text: report request or add expense. Always reply back."""
    try:
        text = (update.message.text or "").strip()
        if not text:
            await update.message.reply_text("Send text (expense or 'report' / 'summary'), or a photo of a receipt.")
            return

        # Report / summary intent
        year, month = parse_report_intent(text)
        if year is not None and month is not None:
            await update.message.reply_chat_action("typing")
            ok, result = await call_monthly_summary(year, month)
            if ok:
                msg = format_report(result)
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text(f"Report failed: {result}")
            return

        # "Can I afford / go for lunch $50?" — check limits
        if detect_afford_intent(text):
            amount, category = parse_afford_query(text)
            if amount is None:
                await update.message.reply_text(
                    "I couldn't find an amount. Try e.g. 'can I spend 50 dollars on lunch?' or 'can I go for lunch that might take $50?'"
                )
                return
            await update.message.reply_chat_action("typing")
            ok_status, status = await call_limits_status_full()
            if not ok_status or not status:
                await update.message.reply_text(
                    "I couldn't check limits (backend may be down). Set limits in the app (Limits & Alerts) and try again."
                )
                return
            reply = format_afford_reply(amount, category, status)
            await update.message.reply_text(reply)
            return

        # Add expense from text
        await update.message.reply_chat_action("typing")
        ok, msg = await call_add_expense(text)
        if ok:
            ok_status, alerts = await call_limits_status()
            if ok_status and alerts:
                msg += format_limit_alerts(alerts)
        await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("handle_message: %s", e)
        await update.message.reply_text(f"Something went wrong: {e}. Try /help or send the expense again.")


def main() -> None:
    if not TELEGRAM_TOKEN:
        print("Set TELEGRAM_BOT_TOKEN (from @BotFather).")
        sys.exit(1)
    print(f"Expense API: {API_URL}")
    if OCR_AVAILABLE:
        print("OCR: enabled (easyocr)")
    else:
        print("OCR: disabled (pip install easyocr for receipt/screenshot support)")
    print("Bot running. Send text, photo, or 'report'. Ctrl+C to stop.")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("date", cmd_date))
    app.add_handler(CommandHandler("time", cmd_date))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
