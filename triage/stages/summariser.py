"""Stage 5: for emails that need action only, say what to do and why. No tools."""

from __future__ import annotations

from ..models import Summary, TriagedEmail
from ..providers import Provider, ProviderError
from .prompting import UNTRUSTED_NOTE, render_email

SYSTEM = f"""You write one item of a morning email digest for the person who received this email.

- task: what they need to do, in one short sentence starting with a verb. Include any deadline.
- why: why it matters, in one short sentence (the consequence of not doing it).
- reply_gist: if they should reply, one line in their voice saying what to reply; otherwise null.

Keep each field under 20 words. Be concrete; don't restate the subject line.

{UNTRUSTED_NOTE}"""


def summarise(items: list[TriagedEmail], provider: Provider, model: str, max_body_chars: int) -> list[TriagedEmail]:
    for item in items:
        if not item.needs_action or item.error:
            continue
        try:
            item.summary = provider.structured(
                model=model, system=SYSTEM, user=render_email(item.email, max_body_chars), schema=Summary
            )
        except ProviderError as e:
            item.error = str(e)
    return items
