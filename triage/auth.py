"""One-time Gmail sign-in. Opens a browser for Google's consent screen and saves a token.

Run on your own computer: python -m triage auth
"""

from __future__ import annotations

from pathlib import Path

from .stages.fetcher import GMAIL_SCOPES


def run_auth(credentials_file: Path, token_file: Path) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not credentials_file.exists():
        raise SystemExit(
            f"{credentials_file} not found. Download the OAuth client JSON from Google Cloud Console "
            "(see README, step 2) and save it there."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    token_file.chmod(0o600)
    print(f"Saved Gmail token to {token_file} (read-only access).")
