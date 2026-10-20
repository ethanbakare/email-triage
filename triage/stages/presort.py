"""Stage 3: everything plain code can decide, so models see less.

Counts, duplicates, ignored senders and obvious newsletters/promotions need no model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from email.utils import parseaddr

from ..models import Category, Email, PreSorted

GMAIL_LABEL_CATEGORIES: dict[str, Category] = {
    "CATEGORY_PROMOTIONS": "promotion",
    "CATEGORY_SOCIAL": "social",
    "CATEGORY_FORUMS": "newsletter",
}


@dataclass
class PreSortResult:
    items: list[PreSorted]
    sender_counts: Counter  # display name -> count, over every fetched email
    total: int
    duplicates: int
    ignored: int


def sender_name(email: Email) -> str:
    name = parseaddr(email.sender)[0].strip().strip('"')
    return name or email.sender_address or "unknown"


def presort(emails: list[Email], newsletter_senders: list[str] = (), ignore_senders: list[str] = ()) -> PreSortResult:
    seen: set[str] = set()
    items: list[PreSorted] = []
    counts: Counter = Counter()
    duplicates = ignored = 0
    for email in emails:
        key = email.id
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        counts[sender_name(email)] += 1
        if _matches(email.sender_address, ignore_senders):
            ignored += 1
            continue
        items.append(PreSorted(email=email, known_category=rule_category(email, newsletter_senders)))
    return PreSortResult(items=items, sender_counts=counts, total=len(seen), duplicates=duplicates, ignored=ignored)


def rule_category(email: Email, newsletter_senders: list[str] = ()) -> Category | None:
    if _matches(email.sender_address, newsletter_senders):
        return "newsletter"
    for label, category in GMAIL_LABEL_CATEGORIES.items():
        if label in email.labels:
            return category
    # An unsubscribe header alone isn't enough: job alerts and bank notices carry one too.
    return None


def _matches(address: str, patterns: list[str]) -> bool:
    # A pattern is a full address ("news@flipboard.com") or a domain ("flipboard.com").
    return any(address == p or address.endswith("@" + p) or address.endswith("." + p) for p in patterns)
