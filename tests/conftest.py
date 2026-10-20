from datetime import datetime, timezone
from pathlib import Path

import pytest

from triage.config import Config
from triage.stages.fetcher import FileMailbox
from triage.store import Store

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "emails.json"
NOW = datetime(2026, 10, 21, 7, 0, tzinfo=timezone.utc)


@pytest.fixture
def cfg():
    c = Config()
    c.newsletter_senders = ["flipboard.com"]
    c.timezone = "UTC"
    return c


@pytest.fixture
def mailbox():
    return FileMailbox(SAMPLE)


@pytest.fixture
def store():
    return Store(":memory:")
