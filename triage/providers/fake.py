"""Offline provider for tests and --dry-run. Answers from simple keyword rules."""

from __future__ import annotations

from ..models import Classification, Summary
from .base import Provider, ProviderError, T

ACTION_WORDS = ("please", "confirm", "deadline", "by friday", "verify", "reply", "action required")


class FakeProvider(Provider):
    def __init__(self):
        self.calls: list[dict] = []

    def structured(self, *, model: str, system: str, user: str, schema: type[T]) -> T:
        self.calls.append({"model": model, "system": system, "user": user, "schema": schema})
        text = user.lower()
        if "fail-this-email" in text:
            raise ProviderError("simulated failure")
        needs_action = any(w in text for w in ACTION_WORDS)
        if schema is Classification:
            category = "jobs" if "job" in text else "personal" if needs_action else "other"
            return schema(category=category, needs_action=needs_action, urgency="high" if needs_action else "low")
        if schema is Summary:
            return schema(task="Reply to this email", why="The sender is waiting on you", reply_gist="Confirm it works")
        raise ProviderError(f"fake provider has no answer for {schema.__name__}")
