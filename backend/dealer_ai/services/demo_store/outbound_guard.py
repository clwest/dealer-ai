"""Milestone 18 · Increment 1 (SESSION_147) — outbound-send-boundary guard.

Per MILESTONE_18_PLANNING.md §5.g Option A + §0.a M18.1 decision 1
(user-confirmed at SESSION_146 open + implementation-time refinement
at SESSION_147 open).

**M18.1 enumeration finding.** The preliminary M18.0 outbound-send-
boundary verb list was aspirational — verified at M18.1 open that
only two verbs currently egress to external networks:

- ``services/llm/openai_provider.py::OpenAIProvider.chat`` — POST
  to ``api.openai.com``.
- ``services/llm/ollama.py::OllamaProvider.chat`` — POST to local
  Ollama endpoint.

Neither is a "customer communication" send-boundary in the §5.g
sense (they are LLM inference calls). The preliminary list named
verbs that would need guards *if/when* they ship — most of those
verbs (M11.4 delivery, M12.5 dispatch, M10 lender adapters, M10
bureau pulls) do not exist today. The M11.4 substrate's docstring
explicitly documents that outbound delivery is deferred.

**M18.1 posture.** Ship the guard toolkit; codify the guard-by-
construction contract for future adapters. Do NOT reroute the
LLM factory (behavior change with UX implications; belongs to a
later "demo LLM cost caps" decision — see M18 retrospective §3
deferrals).

**Contract for future adapters.** Any new verb that egresses to
an external network (email dispatcher, SMS dispatcher, lender
portal, credit bureau, integration adapter, webhook sender, etc.)
MUST call :func:`suppress_if_demo` at the top and short-circuit
if it returns True. The scanner test in
``tests/test_m181_demo_store_substrate.py`` greps ``services/``
for egress patterns and asserts each match is either behind the
guard or on the documented allowlist (currently the two LLM
providers).

The scanner is the enforcement mechanism — it fails loud if a
future adapter forgets the guard.
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import Dealership


_LOGGER = logging.getLogger("dealer_ai.demo_store.outbound")


class SuppressedOutbound:
    """Marker instance returned by adapters when a demo-store guard fires.

    Adapters that would normally return a payload (e.g. an API
    response, a message ID) return an instance of this class instead
    so callers can distinguish "the send completed" from "the send
    was suppressed because this is a demo store." Callers that
    treat any non-None result as success continue to work.
    """

    def __init__(self, verb_name: str, dealership_slug: str) -> None:
        self.verb_name = verb_name
        self.dealership_slug = dealership_slug

    def __repr__(self) -> str:
        return (
            f"SuppressedOutbound(verb={self.verb_name!r}, "
            f"dealership={self.dealership_slug!r})"
        )

    def __bool__(self) -> bool:
        # Truthy so "if result:" callers continue to see success.
        return True


def is_demo_dealership(dealership: "Optional[Dealership]") -> bool:
    """Return True iff ``dealership`` is a demo store.

    Safe to call with ``None`` — returns False so callers without
    tenant context always proceed to real send.
    """
    if dealership is None:
        return False
    return bool(getattr(dealership, "is_demo", False))


def suppress_if_demo(
    dealership: "Optional[Dealership]",
    *,
    verb_name: str,
    **log_extra,
) -> Optional[SuppressedOutbound]:
    """Return a :class:`SuppressedOutbound` marker + log if demo, else None.

    The canonical guard pattern for future adapters:

    .. code-block:: python

        def send_lender_application(dealership, application, **kwargs):
            guard = suppress_if_demo(
                dealership,
                verb_name="services.f_and_i.send_lender_application",
                application_id=application.pk,
            )
            if guard is not None:
                return guard
            # ... real send here ...

    Returns None when the dealership is not a demo store (caller
    proceeds to real send). Returns a :class:`SuppressedOutbound`
    marker when the dealership is a demo store (caller returns
    immediately). Emits a structured INFO log line naming the verb
    + dealership + any caller-supplied extra fields, so the
    suppressed-outbound path is discoverable in operator logs.
    """
    if not is_demo_dealership(dealership):
        return None
    assert dealership is not None  # narrows for the log_extra dict.
    _LOGGER.info(
        "demo-store outbound suppressed",
        extra={
            "verb": verb_name,
            "dealership_slug": dealership.slug,
            **log_extra,
        },
    )
    return SuppressedOutbound(
        verb_name=verb_name, dealership_slug=dealership.slug
    )
