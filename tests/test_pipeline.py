from datetime import timedelta

import pytest

from triage.pipeline import run_once
from triage.providers.fake import FakeProvider
from triage.stages.sender import ConsoleSender

from .conftest import NOW


def test_full_loop_builds_and_sends_digest(cfg, mailbox, store):
    provider, sender = FakeProvider(), ConsoleSender()
    result = run_once(cfg, mailbox, provider, sender, store, now=NOW)

    assert result.emails == 7
    assert len(sender.sent) == 1
    digest = sender.sent[0]
    assert digest.startswith("7 emails, ")
    assert "By sender:" in digest and "By type:" in digest
    assert "Sam Okafor: Reply to this email" in digest  # landlord needs action
    assert "My Bank:" in digest
    # Rule-sorted mail (newsletter, promotion, social) never reached the model.
    seen = " ".join(c["user"] for c in provider.calls)
    assert "Flipboard" not in seen and "Big Shop" not in seen and "LinkedIn" not in seen


def test_next_run_starts_where_last_good_run_ended(cfg, mailbox, store):
    run_once(cfg, mailbox, FakeProvider(), ConsoleSender(), store, now=NOW)
    assert store.last_successful_until() == NOW
    later = run_once(cfg, mailbox, FakeProvider(), ConsoleSender(), store, now=NOW + timedelta(hours=5))
    assert later.emails == 0


def test_counts_only_mode_makes_no_model_calls(cfg, mailbox, store):
    cfg.use_models = False
    sender = ConsoleSender()
    run_once(cfg, mailbox, None, sender, store, now=NOW)
    assert "Counts only" in sender.sent[0]
    assert sender.sent[0].startswith("7 emails")


def test_model_failure_is_surfaced_not_dropped(cfg, mailbox, store):
    class FailingProvider(FakeProvider):
        def structured(self, **kw):
            kw["user"] += " fail-this-email"
            return super().structured(**kw)

    sender = ConsoleSender()
    run_once(cfg, mailbox, FailingProvider(), sender, store, now=NOW)
    assert "couldn't summarise, check it yourself" in sender.sent[0]
    assert "couldn't be processed by the model" in sender.sent[0]


def test_failed_run_is_recorded_and_alerts(cfg, store):
    class BrokenMailbox:
        def fetch_since(self, since, limit):
            raise RuntimeError("token expired")

    sender = ConsoleSender()
    with pytest.raises(RuntimeError):
        run_once(cfg, BrokenMailbox(), FakeProvider(), sender, store, now=NOW)
    assert sender.sent == ["Email digest failed: RuntimeError. Check the log on the machine running it."]
    assert store.last_successful_until() is None
    status, error = store.db.execute("SELECT status, error FROM runs").fetchone()
    assert status == "failed" and "token expired" in error


def test_store_keeps_metadata_not_bodies(cfg, mailbox, store):
    run_once(cfg, mailbox, FakeProvider(), ConsoleSender(), store, now=NOW)
    dump = "\n".join(store.db.iterdump())
    assert "plumber can come Thursday" not in dump
    assert "sam.landlord@example.com" in dump
