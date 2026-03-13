"""
Gmail sync: fetch emails matching a filter query, extract expense from each (subject + body),
save via hybrid extraction, and mark as processed so we don't add duplicates.
Requires: credentials.json (OAuth client) and token.json (from one-time gmail_auth.py).
"""
import base64
import json
import os
import re

# Paths: env or defaults under backend/
_BASE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_JSON", os.path.join(_BASE, "credentials.json"))
TOKEN_PATH = os.environ.get("GMAIL_TOKEN_JSON", os.path.join(_BASE, "token.json"))

# Gmail API
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_gmail_service():
    """Build Gmail API service from token (refresh if needed)."""
    if not GMAIL_AVAILABLE:
        raise RuntimeError("Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Gmail credentials not found: {CREDENTIALS_PATH}")
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _decode_payload(part):
    """Decode body from a message part."""
    if "body" not in part or "data" not in part["body"]:
        return ""
    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")


def _get_body_plain(msg):
    """Get plain-text body from message (multipart or single)."""
    payload = msg.get("payload", {})
    if "body" in payload and payload["body"].get("data"):
        return _decode_payload(payload)
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _decode_payload(part)
        if part.get("mimeType") == "text/html" and not part.get("body", {}).get("data"):
            continue
        if "parts" in part:
            for sub in part["parts"]:
                if sub.get("mimeType") == "text/plain" and sub.get("body", {}).get("data"):
                    return _decode_payload(sub)
    return ""


def _message_to_text(msg) -> str:
    """Subject + snippet + first 800 chars of body for LLM."""
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    subject = headers.get("subject", "")
    snippet = (msg.get("snippet") or "").strip()
    body = _get_body_plain(msg)
    # Strip excessive whitespace and truncate body
    body = re.sub(r"\s+", " ", body)[:800]
    return f"Subject: {subject}\n\n{snippet}\n\n{body}".strip()


def sync_gmail(query: str, max_results: int = 50):
    """
    Fetch messages matching query, for each unprocessed: extract expense via LLM, save, mark processed.
    Returns (added_count, errors_list).
    """
    import database
    import llm_service

    if not GMAIL_AVAILABLE:
        return 0, ["Gmail libraries not installed. pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"]
    if not os.path.exists(CREDENTIALS_PATH):
        return 0, [f"Credentials not found: {CREDENTIALS_PATH}. Run Gmail one-time auth first."]
    if not os.path.exists(TOKEN_PATH):
        return 0, [f"Token not found: {TOKEN_PATH}. Run: python backend/gmail_auth.py"]

    service = _get_gmail_service()
    added = 0
    errors = []

    try:
        result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = result.get("messages", [])
    except Exception as e:
        return 0, [str(e)]

    for m in messages:
        mid = m["id"]
        if database.gmail_is_processed(mid):
            continue
        try:
            msg = service.users().messages().get(userId="me", id=mid, format="full").execute()
            text = _message_to_text(msg)
            if len(text.strip()) < 10:
                database.gmail_mark_processed(mid)
                continue
            import extraction_service
            import merchant_service
            from config import is_auto_verified
            result = extraction_service.extract_expense(text, source_type="gmail")
            is_verified = 1 if is_auto_verified(result.confidence_score) else 0
            database.save_expense(
                date=result.date,
                category=result.category,
                amount=result.amount,
                currency=result.currency,
                raw_text=f"[Gmail] {text[:200]}...",
                merchant=result.merchant,
                subcategory=result.subcategory,
                source_type="gmail",
                confidence_score=result.confidence_score,
                is_verified=is_verified,
                extracted_json=json.dumps(result.extracted_json) if result.extracted_json else None,
                correction_json=None,
            )
            if result.merchant and result.category and (result.confidence_score or 0) >= 0.6:
                merchant_service.remember_merchant_mapping(
                    result.merchant,
                    result.category,
                    subcategory=result.subcategory,
                    display_name=result.merchant,
                    confidence_score=result.confidence_score or 0,
                )
            database.gmail_mark_processed(mid)
            added += 1
        except Exception as e:
            errors.append(f"Message {mid}: {str(e)[:100]}")
            # Still mark as processed so we don't retry forever
            try:
                database.gmail_mark_processed(mid)
            except Exception:
                pass

    return added, errors
