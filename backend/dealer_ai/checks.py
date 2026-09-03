"""Django system checks for the Dealer AI stack.

Runs on ``manage.py check`` (and implicitly at startup for
``manage.py runserver``). Each check must be cheap and read-only —
these fire on every management command and must never touch the
database, network, or filesystem beyond package metadata.
"""

from __future__ import annotations

from typing import List

from django.conf import settings
from django.core.checks import Warning as CheckWarning
from django.core.checks import register


# --- W001: OpenAI SDK / model shape mismatch -------------------------------
#
# The demo walk on 2026-09-03 caught a live outage on the manager coaching
# surface: openai==1.30.5 (May 2024) rejects ``max_completion_tokens`` with
# ``TypeError``, so every gpt-5* request failed at the client boundary and
# ``manager_chat_response`` served a coaching template that looked identical
# to a real reply. The fallback retry in ``OpenAIProvider`` keeps the demo
# running, but the pin is still wrong for the configured model and the
# operator needs to know before the next demo starts.


_REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _model_is_reasoning(model: str) -> bool:
    m = (model or "").lower()
    return any(m.startswith(p) for p in _REASONING_PREFIXES)


@register()
def openai_sdk_model_mismatch(app_configs, **kwargs) -> List[CheckWarning]:
    """W001 — warn one line when the configured OpenAI model needs a
    parameter the installed SDK does not accept.

    Detects the reasoning-model / legacy-SDK combination that caused the
    2026-09-03 outage: the provider will send ``max_completion_tokens``
    for any ``gpt-5*`` / ``o1*`` / ``o3*`` / ``o4*`` model, but SDKs
    older than ``openai==1.45`` do not accept that keyword.

    The provider retries once with ``max_tokens`` when the mismatch
    is detected at request time, but the pin should be bumped so the
    first call succeeds and the retry path is only a safety net.
    """
    provider = (
        getattr(settings, "DEALER_AI_LLM_PROVIDER", "ollama") or "ollama"
    ).lower()
    if provider != "openai":
        return []

    model = getattr(settings, "OPENAI_MODEL", "") or ""
    if not _model_is_reasoning(model):
        return []

    try:
        import inspect

        from openai import OpenAI
    except Exception as exc:  # noqa: BLE001
        return [
            CheckWarning(
                "openai SDK cannot be imported: %s" % exc,
                hint=(
                    "Install `openai` in the active interpreter's venv, "
                    "or set DEALER_AI_LLM_PROVIDER=ollama."
                ),
                id="dealer_ai.W001",
            )
        ]

    try:
        # A cheap probe — no network, no auth required, just the client
        # signature we would call. The OpenAI constructor accepts any
        # string for api_key.
        sig = inspect.signature(
            OpenAI(api_key="check").chat.completions.create
        )
    except Exception as exc:  # noqa: BLE001
        return [
            CheckWarning(
                "openai client could not be introspected: %s" % exc,
                id="dealer_ai.W001",
            )
        ]

    if "max_completion_tokens" in sig.parameters:
        return []

    try:
        from importlib.metadata import version

        installed = version("openai")
    except Exception:  # noqa: BLE001
        installed = "unknown"

    return [
        CheckWarning(
            (
                "openai %s does not accept `max_completion_tokens`, which "
                "the configured OPENAI_MODEL=%s requires; each request "
                "falls back to a legacy retry until the pin is bumped."
            )
            % (installed, model),
            hint=(
                "Bump `openai` inside backend/.venv to >=1.45 (do NOT "
                "reinstall against the pyenv-global interpreter — see "
                "SESSION_224 env-drift note). Or set OPENAI_MODEL to a "
                "non-reasoning model such as gpt-4o-mini."
            ),
            id="dealer_ai.W001",
        )
    ]
