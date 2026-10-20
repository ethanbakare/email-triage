"""Data shapes passed between stages.

Model output is parsed into the pydantic classes below. Anything that does not
fit them is rejected, so a model can only ever hand the next stage these fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "personal",
    "work",
    "jobs",
    "newsletter",
    "promotion",
    "social",
    "finance",
    "admin",
    "receipt",
    "other",
]
Urgency = Literal["high", "medium", "low"]


@dataclass
class Email:
    id: str
    sender: str  # display form, e.g. "Indeed <alerts@indeed.com>"
    sender_address: str  # lowercased address only
    subject: str
    date: datetime
    body: str  # plain text
    labels: list[str] = field(default_factory=list)  # Gmail label ids
    list_unsubscribe: bool = False  # has a List-Unsubscribe header


@dataclass
class PreSorted:
    """Stage 3 output: an email plus what plain code could already tell."""

    email: Email
    known_category: Category | None  # set when rules decide without a model


class Classification(BaseModel):
    category: Category
    needs_action: bool
    urgency: Urgency


class Summary(BaseModel):
    task: str = Field(description="What the reader needs to do, one short sentence")
    why: str = Field(description="Why it matters, one short sentence")
    reply_gist: str | None = Field(
        default=None, description="One line on what to reply, or null if no reply is needed"
    )


@dataclass
class TriagedEmail:
    email: Email
    category: Category
    needs_action: bool
    urgency: Urgency
    summary: Summary | None = None
    error: str | None = None  # set when a model stage failed for this email
