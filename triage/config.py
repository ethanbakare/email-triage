"""Settings come from config.toml; secrets come only from environment variables."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Run window
    lookback_hours: int = 24  # used on the first run, before there is a last-run time
    timezone: str = "Europe/London"
    # Gmail
    credentials_file: Path = Path("secrets/credentials.json")
    token_file: Path = Path("secrets/token.json")
    max_emails: int = 500
    # Models
    provider: str = "anthropic"
    classifier_model: str = "claude-haiku-5-5"
    summariser_model: str = "claude-haiku-5-5"
    max_body_chars: int = 4000  # caps cost per email; the digest says when a body was cut
    use_models: bool = True  # False = stages 1-3 only, counts with no model calls
    # Rules (plain code, stage 3)
    newsletter_senders: list[str] = field(default_factory=list)
    ignore_senders: list[str] = field(default_factory=list)
    # Delivery
    telegram_chat_id: str | None = None
    # Storage
    db_path: Path = Path("data/triage.db")

    @property
    def telegram_bot_token(self) -> str | None:
        return os.environ.get("TELEGRAM_BOT_TOKEN")


def load_config(path: str | Path = "config.toml") -> Config:
    path = Path(path)
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    run, gmail, models = raw.get("run", {}), raw.get("gmail", {}), raw.get("models", {})
    rules, telegram, store = raw.get("rules", {}), raw.get("telegram", {}), raw.get("store", {})
    cfg = Config()
    cfg.lookback_hours = int(run.get("lookback_hours", cfg.lookback_hours))
    cfg.timezone = run.get("timezone", cfg.timezone)
    cfg.credentials_file = Path(gmail.get("credentials_file", cfg.credentials_file))
    cfg.token_file = Path(gmail.get("token_file", cfg.token_file))
    cfg.max_emails = int(gmail.get("max_emails", cfg.max_emails))
    cfg.provider = models.get("provider", cfg.provider)
    cfg.classifier_model = models.get("classifier", cfg.classifier_model)
    cfg.summariser_model = models.get("summariser", cfg.summariser_model)
    cfg.max_body_chars = int(models.get("max_body_chars", cfg.max_body_chars))
    cfg.use_models = bool(models.get("enabled", cfg.use_models))
    cfg.newsletter_senders = [s.lower() for s in rules.get("newsletter_senders", [])]
    cfg.ignore_senders = [s.lower() for s in rules.get("ignore_senders", [])]
    cfg.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID") or telegram.get("chat_id")
    cfg.db_path = Path(store.get("path", cfg.db_path))
    return cfg
