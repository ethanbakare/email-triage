"""The swappable model layer.

Stages only ever call ``Provider.structured``: text in, a validated pydantic
object out. A provider gets no tools, no credentials other than its own API
key, and never sees the mailbox or the phone. Adding another vendor means
writing one more subclass and registering it in ``providers/__init__.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """The model call failed or returned nothing usable."""


class Provider(ABC):
    @abstractmethod
    def structured(self, *, model: str, system: str, user: str, schema: type[T]) -> T:
        """Return ``schema`` filled in by the model, or raise ProviderError."""
