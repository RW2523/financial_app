#!/usr/bin/env python3
"""
One-time Gmail OAuth: run this to open a browser, log in with Google, and save token.json.
Before running:
  1. Go to https://console.cloud.google.com/
  2. Create a project (or use existing), enable "Gmail API"
  3. Create OAuth 2.0 credentials (Desktop app), download JSON
  4. Save as backend/credentials.json (or set GMAIL_CREDENTIALS_JSON)
Then run: python backend/gmail_auth.py
"""
import os
import sys

_BASE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_JSON", os.path.join(_BASE, "credentials.json"))
TOKEN_PATH = os.environ.get("GMAIL_TOKEN_JSON", os.path.join(_BASE, "token.json"))

def main():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError:
        print("Install: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        sys.exit(1)
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"Place your OAuth client JSON at: {CREDENTIALS_PATH}")
        print("Get it from: Google Cloud Console -> APIs & Services -> Credentials -> Create OAuth client (Desktop)")
        sys.exit(1)
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {TOKEN_PATH}. You can run Gmail sync now.")


if __name__ == "__main__":
    main()
