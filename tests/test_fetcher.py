import base64
from pathlib import Path

import pytest

from triage.stages.fetcher import GMAIL_SCOPES, load_credentials, parse_gmail_message


def test_credentials_from_env_are_read_only():
    env = {"GMAIL_CLIENT_ID": "id", "GMAIL_CLIENT_SECRET": "secret", "GMAIL_REFRESH_TOKEN": "refresh"}
    creds = load_credentials(Path("missing.json"), env=env)
    assert creds.refresh_token == "refresh"
    assert list(creds.scopes) == GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]


def test_missing_credentials_say_what_to_do():
    with pytest.raises(RuntimeError, match="GMAIL_REFRESH_TOKEN"):
        load_credentials(Path("missing.json"), env={})


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_parses_headers_and_prefers_plain_text():
    msg = {
        "id": "abc",
        "labelIds": ["INBOX", "CATEGORY_UPDATES"],
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": "Indeed <Alerts@Indeed.com>"},
                {"name": "Subject", "value": "New jobs"},
                {"name": "Date", "value": "Tue, 20 Oct 2026 07:30:00 +0000"},
                {"name": "List-Unsubscribe", "value": "<mailto:x@indeed.com>"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": b64("Plain body")}},
                {"mimeType": "text/html", "body": {"data": b64("<p>HTML body</p>")}},
                {"mimeType": "text/plain", "filename": "cv.txt", "body": {"data": b64("attachment")}},
            ],
        },
    }
    e = parse_gmail_message(msg)
    assert e.sender_address == "alerts@indeed.com"
    assert e.subject == "New jobs"
    assert e.body == "Plain body"
    assert e.list_unsubscribe is True
    assert e.date.year == 2026


def test_falls_back_to_html_without_scripts():
    msg = {
        "id": "x",
        "payload": {
            "mimeType": "text/html",
            "headers": [{"name": "From", "value": "a@b.com"}],
            "body": {"data": b64("<style>.a{}</style><script>evil()</script><p>Hello&amp;bye</p><br>Line two")},
        },
        "internalDate": "1792531600000",
    }
    e = parse_gmail_message(msg)
    assert "evil" not in e.body and ".a{}" not in e.body
    assert "Hello&bye" in e.body and "Line two" in e.body
