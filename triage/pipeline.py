"""One run of the loop: stages 2 to 7, in order. Stage 1 (the schedule) is cron.

Each stage gets only what it needs: the mailbox object exists only in fetch,
the provider only in classify/summarise, the sender only at the end.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import Config
from .models import TriagedEmail
from .providers import Provider
from .stages.classifier import classify
from .stages.digest import build_digest
from .stages.fetcher import Mailbox
from .stages.presort import presort
from .stages.sender import Sender
from .stages.summariser import summarise
from .store import Store


@dataclass
class RunResult:
    digest: str
    emails: int
    triaged: list[TriagedEmail] | None


def run_once(
    cfg: Config,
    mailbox: Mailbox,
    provider: Provider | None,
    sender: Sender,
    store: Store,
    now: datetime | None = None,
) -> RunResult:
    now = now or datetime.now(timezone.utc)
    since = store.last_successful_until() or now - timedelta(hours=cfg.lookback_hours)
    try:
        emails = mailbox.fetch_since(since, cfg.max_emails)  # stage 2
        sorted_ = presort(emails, cfg.newsletter_senders, cfg.ignore_senders)  # stage 3
        triaged = None
        if cfg.use_models:
            if provider is None:
                raise ValueError("models are enabled but no provider was given")
            triaged = classify(sorted_.items, provider, cfg.classifier_model, cfg.max_body_chars)  # stage 4
            triaged = summarise(triaged, provider, cfg.summariser_model, cfg.max_body_chars)  # stage 5
        tz = ZoneInfo(cfg.timezone)
        digest = build_digest(sorted_, triaged, since.astimezone(tz), now.astimezone(tz))  # stage 6
        sender.send(digest)  # stage 7
    except Exception as e:
        store.record_run(now, since, now, "failed", error=f"{type(e).__name__}: {e}")
        try:
            sender.send(f"Email digest failed: {type(e).__name__}. Check the log on the machine running it.")
        except Exception:
            pass
        raise
    store.record_run(now, since, now, "ok", emails=sorted_.total, digest=digest, triaged=triaged)
    return RunResult(digest=digest, emails=sorted_.total, triaged=triaged)
