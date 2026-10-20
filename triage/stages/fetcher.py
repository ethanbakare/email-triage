"""Stage 2: download new mail, read-only, and strip it to plain text.

This is the only code that holds the Gmail token, and the token only has the
gmail.readonly scope, so nothing downstream can send, delete or archive.
"""

from __future__ import annotations

import base64
import html
import json
import re
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Protocol

from ..models import Email

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class Mailbox(Protocol):
    def fetch_since(self, since: datetime, limit: int) -> list[Email]: ...


class GmailMailbox:
    def __init__(self, token_file: Path):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(token_file), GMAIL_SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        if not creds.valid:
            raise RuntimeError(f"Gmail token in {token_file} is invalid; run `python -m triage auth` again")
        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    def fetch_since(self, since: datetime, limit: int) -> list[Email]:
        query = f"after:{int(since.timestamp())} -in:chats"
        ids: list[str] = []
        request = self.service.users().messages().list(userId="me", q=query, maxResults=min(limit, 500))
        while request is not None and len(ids) < limit:
            page = request.execute()
            ids.extend(m["id"] for m in page.get("messages", []))
            request = self.service.users().messages().list_next(request, page)
        messages = (
            self.service.users().messages().get(userId="me", id=i, format="full").execute() for i in ids[:limit]
        )
        return [parse_gmail_message(m) for m in messages]


class FileMailbox:
    """Reads emails from a JSON file. Used by tests and `--dry-run`."""

    def __init__(self, path: Path):
        self.path = path

    def fetch_since(self, since: datetime, limit: int) -> list[Email]:
        rows = json.loads(self.path.read_text())
        emails = [
            Email(
                id=r["id"],
                sender=r["sender"],
                sender_address=parseaddr(r["sender"])[1].lower(),
                subject=r.get("subject", ""),
                date=datetime.fromisoformat(r["date"]),
                body=r.get("body", ""),
                labels=r.get("labels", []),
                list_unsubscribe=r.get("list_unsubscribe", False),
            )
            for r in rows
        ]
        return [e for e in emails if e.date >= since][:limit]


def parse_gmail_message(msg: dict) -> Email:
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    sender = headers.get("from", "")
    try:
        date = parsedate_to_datetime(headers["date"])
    except (KeyError, TypeError, ValueError):
        date = datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000, tz=timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return Email(
        id=msg["id"],
        sender=sender,
        sender_address=parseaddr(sender)[1].lower(),
        subject=headers.get("subject", ""),
        date=date,
        body=extract_text(payload),
        labels=msg.get("labelIds", []),
        list_unsubscribe="list-unsubscribe" in headers,
    )


def extract_text(payload: dict) -> str:
    """Prefer text/plain parts; fall back to HTML with tags stripped. Attachments are skipped."""
    plain = list(_parts(payload, "text/plain"))
    if plain:
        return "\n".join(plain).strip()
    return "\n".join(html_to_text(h) for h in _parts(payload, "text/html")).strip()


def _parts(part: dict, mime: str) -> Iterable[str]:
    if part.get("filename"):
        return
    if part.get("mimeType") == mime and part.get("body", {}).get("data"):
        yield base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for child in part.get("parts", []) or []:
        yield from _parts(child, mime)


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()
