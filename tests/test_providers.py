from types import SimpleNamespace

import pytest

from triage.models import Classification
from triage.providers import ProviderError, get_provider
from triage.providers.anthropic_provider import AnthropicProvider
from triage.stages.sender import split_message


def provider_returning(response):
    p = AnthropicProvider(api_key="test-key")
    p.client = SimpleNamespace(messages=SimpleNamespace(parse=lambda **kw: response))
    return p


def test_anthropic_returns_parsed_output():
    parsed = Classification(category="work", needs_action=True, urgency="high")
    p = provider_returning(SimpleNamespace(stop_reason="end_turn", parsed_output=parsed))
    assert p.structured(model="m", system="s", user="u", schema=Classification) == parsed


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_anthropic_bad_stops_raise(stop):
    p = provider_returning(SimpleNamespace(stop_reason=stop, parsed_output=None))
    with pytest.raises(ProviderError):
        p.structured(model="m", system="s", user="u", schema=Classification)


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError):
        get_provider("nope")


def test_split_message_respects_telegram_limit():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(200))
    chunks = split_message(text, limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert "\n".join(chunks) == text
