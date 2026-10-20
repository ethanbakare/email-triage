"""Command line entry point.

    python -m triage auth                 # one-time Gmail sign-in
    python -m triage run                  # one full run, sends to Telegram
    python -m triage run --dry-run        # sample emails, fake model, prints instead of sending
    python -m triage run --no-model       # counts only, no model calls
    python -m triage run --print          # real Gmail and model, print instead of sending
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .pipeline import run_once
from .providers import get_provider
from .store import Store

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "emails.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="triage")
    parser.add_argument("--config", default="config.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("auth", help="sign in to Gmail once and save a read-only token")
    sub.add_parser("telegram-chat-id", help="print the chat id of whoever last messaged your bot")
    run = sub.add_parser("run", help="fetch, triage and send one digest")
    run.add_argument("--dry-run", action="store_true", help="sample emails + fake model, print the digest")
    run.add_argument("--no-model", action="store_true", help="counts only, skip model stages")
    run.add_argument("--print", action="store_true", help="print the digest instead of sending it")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)

    if args.command == "auth":
        from .auth import run_auth

        run_auth(cfg.credentials_file, cfg.token_file)
        return 0

    if args.command == "telegram-chat-id":
        import requests

        if not cfg.telegram_bot_token:
            raise SystemExit("Set TELEGRAM_BOT_TOKEN first (see README, step 3).")
        url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/getUpdates"
        updates = requests.get(url, timeout=30).json().get("result", [])
        chats = [u["message"]["chat"] for u in updates if "message" in u]
        if not chats:
            raise SystemExit("No messages yet. Send any message to your bot in Telegram, then run this again.")
        print(f"TELEGRAM_CHAT_ID={chats[-1]['id']}")
        return 0

    from .stages.sender import ConsoleSender, TelegramSender

    if args.no_model:
        cfg.use_models = False
    if args.dry_run:
        from datetime import datetime, timezone

        from .stages.fetcher import FileMailbox

        mailbox = FileMailbox(SAMPLE)
        provider = get_provider("fake") if cfg.use_models else None
        now = datetime(2026, 10, 21, 7, 0, tzinfo=timezone.utc)  # the sample emails are from the day before
        run_once(cfg, mailbox, provider, ConsoleSender(), Store(":memory:"), now=now)
        return 0

    from .stages.fetcher import GmailMailbox

    mailbox = GmailMailbox(cfg.token_file)
    provider = get_provider(cfg.provider) if cfg.use_models else None
    sender = ConsoleSender() if args.print else TelegramSender(cfg.telegram_bot_token, cfg.telegram_chat_id)
    try:
        run_once(cfg, mailbox, provider, sender, Store(cfg.db_path))
    except Exception as e:
        print(f"run failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
