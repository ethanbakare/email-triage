"""Stage 7: deliver the finished digest. Holds the Telegram token and nothing else.

It sends to one fixed chat id from config, as plain text (no Markdown parsing),
so nothing in the digest can redirect it or change how it is sent.
"""

from __future__ import annotations

from typing import Protocol

import requests

TELEGRAM_LIMIT = 4096


class Sender(Protocol):
    def send(self, text: str) -> None: ...


class ConsoleSender:
    def __init__(self):
        self.sent: list[str] = []

    def send(self, text: str) -> None:
        self.sent.append(text)
        print(text)


class TelegramSender:
    def __init__(self, bot_token: str, chat_id: str):
        if not bot_token or not chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must both be set")
        self.url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        for chunk in split_message(text):
            r = requests.post(self.url, json={"chat_id": self.chat_id, "text": chunk}, timeout=30)
            if r.status_code != 200:
                # Don't echo the URL: it contains the bot token.
                raise RuntimeError(f"Telegram send failed: HTTP {r.status_code} {r.text[:200]}")


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
