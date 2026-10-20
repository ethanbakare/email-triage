from __future__ import annotations

import anthropic

from .base import Provider, ProviderError, T


class AnthropicProvider(Provider):
    def __init__(self, api_key: str | None = None, max_tokens: int = 1024):
        # With api_key=None the SDK reads ANTHROPIC_API_KEY or an `ant auth login` profile.
        self.client = anthropic.Anthropic(api_key=api_key)
        self.max_tokens = max_tokens

    def structured(self, *, model: str, system: str, user: str, schema: type[T]) -> T:
        try:
            response = self.client.messages.parse(
                model=model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
            )
        except anthropic.RateLimitError as e:
            raise ProviderError(f"rate limited: {e}") from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError(f"connection error: {e}") from e

        if response.stop_reason == "refusal":
            raise ProviderError("model declined this email")
        if response.stop_reason == "max_tokens":
            raise ProviderError("output cut off at max_tokens")
        if response.parsed_output is None:
            raise ProviderError("no structured output returned")
        return response.parsed_output
