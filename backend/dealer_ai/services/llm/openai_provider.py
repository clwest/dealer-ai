"""OpenAI provider — gated behind config so Ollama works without an API key."""

from __future__ import annotations

import logging
import re
from typing import Iterable

from .base import ChatMessage, LLMProvider, ProviderUnavailable

logger = logging.getLogger(__name__)

# Model families that require the reasoning-model parameter shape:
#   - max_tokens is rejected; use max_completion_tokens.
#   - temperature only accepts the default (1); any other value is a 400.
# Detected by name prefix so future variants (gpt-5.1, o4, etc.) fall into
# the same bucket automatically.
_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")

# SDK-drift retry marker. openai==1.30.5 (May 2024) predates reasoning
# models entirely and its ``chat.completions.create()`` Python signature
# has no ``max_completion_tokens`` keyword. The SDK does, however, ship
# an ``extra_body`` kwarg that forwards arbitrary JSON fields into the
# request body without signature validation (see the local
# ``openai/resources/chat/completions.py``). When the demo runs on that
# pin against a gpt-5* model we retry once with the reasoning shape
# carried in ``extra_body`` so the request reaches the API with the
# right parameter name — the legacy ``max_tokens`` fallback shipped
# earlier does not work: the API rejects it with "Unsupported
# parameter: 'max_tokens' is not supported with this model. Use
# 'max_completion_tokens' instead." See ``dealer_ai.checks`` and
# ``tests/test_llm_provider_guard.py``.
_UNEXPECTED_KWARG_RE = re.compile(
    r"unexpected keyword argument ['\"]?"
    r"(max_completion_tokens|reasoning_effort|max_tokens|temperature)['\"]?"
)


def _is_reasoning_model(model: str) -> bool:
    m = (model or "").lower()
    return any(m.startswith(p) for p in _REASONING_PREFIXES)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, *, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider.")
        # Lazy import so ollama-only setups don't need the openai package.
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model

    def _build_params(self, messages, *, temperature: float, max_tokens: int) -> dict:
        params: dict = {
            "model": self.model,
            "messages": self.normalize(messages),
        }
        if _is_reasoning_model(self.model):
            # Reasoning models burn tokens on internal reasoning before
            # producing content, so a caller-specified 800 for content
            # often leaves nothing for the actual answer. Double it as
            # a floor so the visible reply has room to land.
            params["max_completion_tokens"] = max(max_tokens * 2, 1200)
        else:
            params["max_tokens"] = max_tokens
            params["temperature"] = temperature
        return params

    def _extra_body_reasoning_params(self, params: dict, *, max_tokens: int) -> dict:
        """Rebuild params using ``extra_body`` for the reasoning-model shape.

        The SDK's ``extra_body`` kwarg forwards arbitrary JSON fields
        into the request body without signature validation, so a
        client whose Python signature lacks ``max_completion_tokens``
        can still deliver it to the API. Temperature is omitted —
        reasoning models only accept the default and any explicit
        value is a 400 — and ``max_tokens`` is omitted because the
        API rejects it for these families.
        """
        return {
            "model": params["model"],
            "messages": params["messages"],
            "extra_body": {
                "max_completion_tokens": max(max_tokens * 2, 1200),
            },
        }

    def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 800,
        **kwargs,
    ) -> str:
        params = self._build_params(
            messages, temperature=temperature, max_tokens=max_tokens
        )

        try:
            resp = self._client.chat.completions.create(**params)
        except TypeError as exc:
            # SDK-drift: the client rejected a keyword the current model
            # family expects. Retry once carrying max_completion_tokens
            # in extra_body so the SDK's signature stops rejecting it
            # and the API sees the correct parameter name. Any other
            # TypeError means our own call site is wrong and should
            # not be papered over.
            if _is_reasoning_model(self.model) and _UNEXPECTED_KWARG_RE.search(str(exc)):
                logger.warning(
                    "OpenAI SDK/model drift — retrying with "
                    "extra_body={max_completion_tokens} shape "
                    "(model=%s, first_error=%s). "
                    "See dealer_ai.checks W001 for the underlying pin mismatch.",
                    self.model,
                    exc,
                )
                retry_params = self._extra_body_reasoning_params(
                    params, max_tokens=max_tokens
                )
                try:
                    resp = self._client.chat.completions.create(**retry_params)
                except Exception as retry_exc:  # noqa: BLE001
                    logger.warning(
                        "OpenAI extra_body retry failed: %s", retry_exc
                    )
                    raise ProviderUnavailable(
                        f"OpenAI request failed after SDK-drift retry: {retry_exc}"
                    ) from retry_exc
            else:
                logger.warning("OpenAI request failed: %s", exc)
                raise ProviderUnavailable(f"OpenAI request failed: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            # Network error, auth failure, rate limit, API error, etc.
            # Callers at surface boundaries decide the user-visible
            # response; we surface an outage rather than a normal reply
            # that happens to read like one.
            logger.warning("OpenAI request failed: %s", exc)
            raise ProviderUnavailable(f"OpenAI request failed: {exc}") from exc

        choice = resp.choices[0]
        return (choice.message.content or "").strip()
