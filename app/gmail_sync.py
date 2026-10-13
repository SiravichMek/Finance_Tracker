"""Daily Gmail sync worker. Uses Gmail API readonly OAuth credentials."""
from __future__ import annotations
import base64
import json
import logging
import os
from email.utils import parsedate_to_datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.db import connect, init_db, add_transaction
from app.parsers import parse_transaction

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("finance-gmail-sync")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def decode_part(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def collect_text(payload: dict) -> str:
    chunks = []
    mime = payload.get("mimeType", "")
    body = payload.get("body", {}).get("data")
    if body and (mime == "text/plain" or not mime):
        chunks.append(decode_part(body))
    for part in payload.get("parts", []) or []:
        chunks.append(collect_text(part))
    # HTML-only messages are intentionally not parsed yet; add a sanitized HTML-to-text fallback if needed.
    return "\n".join(x for x in chunks if x)


def gmail_client():
    token_path = os.getenv("GMAIL_TOKEN_PATH", "/secrets/token.json")
    with open(token_path, encoding="utf-8") as f:
        token_info = json.load(f)
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    if not creds.valid:
        # Refresh is handled by google-auth when refresh token is present; persist refreshed token to mounted storage
        from google.auth.transport.requests import Request
        if creds.expired and creds.refresh_token:
            # Refresh in memory for this run; the long-lived refresh token remains in the mounted secret.
            creds.refresh(Request())
        else:
            raise RuntimeError("Gmail OAuth token is invalid; re-authorize and replace token.json")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def main():
    db = connect()
    init_db(db)
    run_id = db.execute("INSERT INTO sync_runs DEFAULT VALUES RETURNING id").fetchone()[0]
    db.commit()
    seen = imported = failures = 0
    try:
        service = gmail_client()
        # Search recent mail from both banks. Widen the lookback to 14 days so missed CronJob runs recover.
        query = 'newer_than:14d {"krungsri app" "K PLUS Service" "PromptPay Funds Transfer"}'
        response = service.users().messages().list(userId="me", q=query, maxResults=500).execute()
        messages = response.get("messages", [])
        while response.get("nextPageToken"):
            response = service.users().messages().list(userId="me", q=query, maxResults=500,
                                                       pageToken=response["nextPageToken"]).execute()
            messages.extend(response.get("messages", []))
        for item in messages:
            seen += 1
            msg = service.users().messages().get(userId="me", id=item["id"], format="full").execute()
            text = collect_text(msg.get("payload", {}))
            # Some providers send HTML-only email. Do not silently create malformed transactions.
            tx = parse_transaction(text)
            if not tx:
                failures += 1
                log.warning("Could not parse matching Gmail message id=%s; subject/body format may need a parser update", item["id"])
                continue
            if add_transaction(db, item["id"], tx):
                imported += 1
        db.execute("UPDATE sync_runs SET finished_at=NOW(), messages_seen=%s, transactions_imported=%s, parse_failures=%s, status='success' WHERE id=%s",
                   (seen, imported, failures, run_id))
        db.commit()
        log.info("Gmail sync complete: seen=%s imported=%s parse_failures=%s", seen, imported, failures)
    except Exception as exc:
        db.execute("UPDATE sync_runs SET finished_at=NOW(), messages_seen=%s, transactions_imported=%s, parse_failures=%s, status='failed', error=%s WHERE id=%s",
                   (seen, imported, failures, str(exc)[:2000], run_id))
        db.commit()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
