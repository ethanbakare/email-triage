"""Stage 4: fixed questions per email. Text in, a Classification out; no tools."""

from __future__ import annotations

from ..models import Classification, PreSorted, TriagedEmail
from ..providers import Provider, ProviderError
from .prompting import UNTRUSTED_NOTE, render_email

SYSTEM = f"""You triage one email for a busy person reading a morning digest.

Answer three questions:
- category: personal, work, jobs, newsletter, promotion, social, finance, admin, receipt or other.
- needs_action: true only if the reader must do something (reply, pay, confirm, book, decide, apply).
  Marketing, newsletters and plain notifications are false.
- urgency: high if it has a deadline within about 3 days or real consequences if missed,
  medium if it needs doing this week, low otherwise.

{UNTRUSTED_NOTE}"""


def classify(items: list[PreSorted], provider: Provider, model: str, max_body_chars: int) -> list[TriagedEmail]:
    out: list[TriagedEmail] = []
    for item in items:
        email = item.email
        if item.known_category is not None:
            # Rules already decided (promotions, social, listed newsletters): no model call.
            out.append(TriagedEmail(email=email, category=item.known_category, needs_action=False, urgency="low"))
            continue
        try:
            c = provider.structured(
                model=model, system=SYSTEM, user=render_email(email, max_body_chars), schema=Classification
            )
            out.append(TriagedEmail(email=email, category=c.category, needs_action=c.needs_action, urgency=c.urgency))
        except ProviderError as e:
            # Unclassified mail is surfaced, not dropped, so nothing silently disappears.
            out.append(TriagedEmail(email=email, category="other", needs_action=True, urgency="medium", error=str(e)))
    return out
