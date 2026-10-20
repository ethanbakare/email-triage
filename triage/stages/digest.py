"""Stage 6: fill a fixed template. Plain code, no model, so the layout never drifts."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from ..models import TriagedEmail
from .presort import PreSortResult, sender_name

URGENCY_ORDER = {"high": 0, "medium": 1, "low": 2}
TOP_SENDERS = 5
MAX_ITEMS = 15


def _top(counter: Counter, n: int) -> str:
    common = counter.most_common(n)
    rest = sum(counter.values()) - sum(c for _, c in common)
    parts = [f"{name} {count}" for name, count in common]
    if rest:
        parts.append(f"other {rest}")
    return " · ".join(parts) if parts else "none"


def build_digest(
    presorted: PreSortResult,
    triaged: list[TriagedEmail] | None,
    since: datetime,
    until: datetime,
) -> str:
    """``triaged`` is None in counts-only mode (no model stages ran)."""
    window = f"{since:%a %d %b %H:%M} to {until:%a %d %b %H:%M}"
    lines: list[str] = []

    if triaged is None:
        lines.append(f"{presorted.total} emails ({window})")
        lines += ["", f"By sender: {_top(presorted.sender_counts, TOP_SENDERS)}"]
        lines += ["", "Counts only: model stages are switched off."]
        return "\n".join(lines)

    actions = [t for t in triaged if t.needs_action]
    actions.sort(key=lambda t: (URGENCY_ORDER[t.urgency], t.email.date))
    lines.append(f"{presorted.total} emails, {len(actions)} need you ({window})")
    lines += ["", f"By sender: {_top(presorted.sender_counts, TOP_SENDERS)}"]
    lines.append(f"By type: {_top(Counter(t.category for t in triaged), 6)}")

    if actions:
        lines += ["", "Act on"]
        for i, t in enumerate(actions[:MAX_ITEMS], 1):
            who = sender_name(t.email)
            flag = " [urgent]" if t.urgency == "high" else ""
            if t.summary:
                lines.append(f"{i}. {who}: {t.summary.task}{flag}")
                lines.append(f"   Why: {t.summary.why}")
                if t.summary.reply_gist:
                    lines.append(f"   Reply: {t.summary.reply_gist}")
            else:
                # A model stage failed for this one; show the raw subject so it isn't lost.
                lines.append(f"{i}. {who}: \"{t.email.subject}\" (couldn't summarise, check it yourself)")
        if len(actions) > MAX_ITEMS:
            lines.append(f"…and {len(actions) - MAX_ITEMS} more")
    else:
        lines += ["", "Nothing needs you today."]

    failed = sum(1 for t in triaged if t.error)
    if failed:
        lines += ["", f"{failed} email(s) couldn't be processed by the model and are listed above to check."]
    return "\n".join(lines)
