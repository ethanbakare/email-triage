from __future__ import annotations

from .base import Provider, ProviderError


def get_provider(name: str) -> Provider:
    """Build the provider named in config. Imports are lazy so unused SDKs needn't be installed."""
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if name == "fake":
        from .fake import FakeProvider

        return FakeProvider()
    raise ValueError(f"unknown provider {name!r}; expected 'anthropic' or 'fake'")


__all__ = ["Provider", "ProviderError", "get_provider"]
