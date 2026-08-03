"""Outbound-send-boundary guard (M18.1 origin; refactored at M19.1).

**Original scope (M18.1).** Per MILESTONE_18_PLANNING.md §5.g
Option A + §0.a M18.1 decision 1 (user-confirmed at SESSION_146
open + implementation-time refinement at SESSION_147 open).
Shipped the guard toolkit + a scanner test that fails loud if any
future ``services/`` verb egresses without calling the guard.

**M19.1 refactor.** Per MILESTONE_19_PLANNING.md §5.g Option A +
§0.a M19.1 decision 2 (user-confirmed at SESSION_154 open). The
guard's **predicate** shifted from a tenant-type inference
(``is_demo``) to an explicit **send-policy field** on
:class:`models.Dealership` (``outbound_enabled``). Rationale:

- Demo dealerships and pilot dealerships both start with
  ``outbound_enabled=False``. Nothing changes for the M18.1
  outbound-egress scanner contract.
- Live production dealerships (created via a future non-M19 path)
  default ``outbound_enabled=False`` too; an operator explicitly
  flips to True at go-live.
- Pilots that need controlled outbound enablement (per-verb code
  review) are a single-column flip on the Dealership row — no
  tenant-type reclassification required.
- Auditability: the Dealership row's ``outbound_enabled`` state at
  any time answers "was outbound enabled when X happened?" — a
  question the tenant-type-based predicate couldn't answer cleanly.
- Orthogonality: tenant-type flags describe **what the record is**
  (``is_demo``, ``is_pilot``); the policy field describes **what
  the platform is allowed to do on the tenant's behalf**.

**Backward compatibility.** :func:`suppress_if_demo` is preserved
as a deprecated alias that delegates to
:func:`suppress_if_outbound_disabled`. Existing callers continue
to work without modification. :func:`is_demo_dealership` is
preserved as a **diagnostic** helper (still returns True iff
``is_demo=True``) so archetype builders + admin surfaces that
specifically care about tenant type continue to work. A new
:func:`is_pilot_dealership` diagnostic helper mirrors it for
pilot-type inference.

**Contract for adapters (unchanged).** Any verb that egresses to
an external network MUST call :func:`suppress_if_outbound_disabled`
at the top and short-circuit if it returns a non-None marker. The
scanner test in ``tests/test_m181_demo_store_substrate.py`` +
extension at ``tests/test_m191_pilot_substrate.py`` enforces this.

**M18.1 enumeration finding still applies.** Only two verbs
currently egress (the two LLM providers). Both remain on the
scanner allowlist — the demo-aware LLM router remains deferred
per M18 retrospective §3.
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...models import Dealership


_LOGGER = logging.getLogger("dealer_ai.demo_store.outbound")


class SuppressedOutbound:
    """Marker instance returned by adapters when the outbound guard fires.

    Adapters that would normally return a payload (e.g. an API
    response, a message ID) return an instance of this class instead
    so callers can distinguish "the send completed" from "the send
    was suppressed because the outbound policy is disabled." Callers
    that treat any non-None result as success continue to work.

    The class name references "outbound" not "demo-store" so the
    M19.1 refactor semantics read correctly. Instances retain the
    ``verb_name`` + ``dealership_slug`` fields callers already
    depend on.
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


# ---------------------------------------------------------------------------
# Diagnostic tenant-type helpers (M19.1 refactor — no longer the guard predicate)
# ---------------------------------------------------------------------------


def is_demo_dealership(dealership: "Optional[Dealership]") -> bool:
    """Diagnostic — return True iff ``dealership.is_demo`` is True.

    Safe to call with ``None`` — returns False.

    **M19.1 note.** This is now a diagnostic helper only —
    callers that need to know "is this a demo store?" for
    tenant-type reasons (e.g. archetype builder dispatch, admin
    surface tenant-type badges) use it. **The outbound guard no
    longer uses this predicate.** For outbound suppression, call
    :func:`suppress_if_outbound_disabled`.
    """
    if dealership is None:
        return False
    return bool(getattr(dealership, "is_demo", False))


def is_pilot_dealership(dealership: "Optional[Dealership]") -> bool:
    """Diagnostic — return True iff ``dealership.is_pilot`` is True.

    New at M19.1 per §0.a M19.1 decision 2. Companion to
    :func:`is_demo_dealership`. Safe to call with ``None`` —
    returns False.

    Callers that need to know "is this a pilot store?" for tenant-
    type reasons use this. Not used by the outbound guard.
    """
    if dealership is None:
        return False
    return bool(getattr(dealership, "is_pilot", False))


def is_outbound_enabled(dealership: "Optional[Dealership]") -> bool:
    """Return True iff ``dealership.outbound_enabled`` is True.

    Safe to call with ``None`` — returns False (a caller without a
    tenant context has no policy context; suppress by default).

    **This is the predicate the outbound guard uses at M19.1+.**
    """
    if dealership is None:
        return False
    return bool(getattr(dealership, "outbound_enabled", False))


# ---------------------------------------------------------------------------
# The canonical guard (M19.1 refactor)
# ---------------------------------------------------------------------------


def suppress_if_outbound_disabled(
    dealership: "Optional[Dealership]",
    *,
    verb_name: str,
    **log_extra,
) -> Optional[SuppressedOutbound]:
    """Return a :class:`SuppressedOutbound` marker + log if outbound is disabled, else None.

    The canonical guard pattern for adapters at M19.1+:

    .. code-block:: python

        def send_lender_application(dealership, application, **kwargs):
            guard = suppress_if_outbound_disabled(
                dealership,
                verb_name="services.f_and_i.send_lender_application",
                application_id=application.pk,
            )
            if guard is not None:
                return guard
            # ... real send here ...

    Returns None when the dealership has ``outbound_enabled=True``
    (caller proceeds to real send). Returns a
    :class:`SuppressedOutbound` marker when
    ``outbound_enabled=False`` (caller returns immediately). Also
    returns a marker for ``dealership=None`` because a caller
    without tenant context has no policy context — suppress by
    default.

    Emits a structured INFO log line naming the verb + dealership +
    any caller-supplied extra fields, so the suppressed-outbound
    path is discoverable in operator logs.
    """
    if is_outbound_enabled(dealership):
        return None
    if dealership is None:
        # No dealership context — log without a slug field.
        _LOGGER.info(
            "outbound suppressed (no tenant context)",
            extra={"verb": verb_name, **log_extra},
        )
        return SuppressedOutbound(
            verb_name=verb_name, dealership_slug=""
        )
    _LOGGER.info(
        "outbound suppressed",
        extra={
            "verb": verb_name,
            "dealership_slug": dealership.slug,
            "is_demo": bool(getattr(dealership, "is_demo", False)),
            "is_pilot": bool(getattr(dealership, "is_pilot", False)),
            **log_extra,
        },
    )
    return SuppressedOutbound(
        verb_name=verb_name, dealership_slug=dealership.slug
    )


# ---------------------------------------------------------------------------
# Deprecated alias (M19.1) — preserves M18.1 API surface for existing callers
# ---------------------------------------------------------------------------


def suppress_if_demo(
    dealership: "Optional[Dealership]",
    *,
    verb_name: str,
    **log_extra,
) -> Optional[SuppressedOutbound]:
    """Deprecated alias — delegates to :func:`suppress_if_outbound_disabled`.

    **Deprecated at M19.1** per §0.a M19.1 decision 2. Preserved as
    a shim so M18.1-era callers continue to work; emits a
    :class:`DeprecationWarning` on first use per call site.

    Behavior note: at M18.1 this checked ``is_demo``; at M19.1+ it
    checks ``outbound_enabled``. For existing M18-era demo
    dealerships this is behaviorally identical (both had outbound
    suppressed; both continue to). For pilot dealerships, this
    correctly suppresses (their ``outbound_enabled`` defaults to
    False). If any caller depended on "demo but outbound enabled"
    behavior — which was architecturally impossible at M18.1 —
    they need to reconsider their guard call.

    New callers should call :func:`suppress_if_outbound_disabled`
    directly.
    """
    warnings.warn(
        "suppress_if_demo is deprecated; call "
        "suppress_if_outbound_disabled instead. See "
        "MILESTONE_19_PLANNING.md §0.a M19.1 decision 2.",
        DeprecationWarning,
        stacklevel=2,
    )
    return suppress_if_outbound_disabled(
        dealership, verb_name=verb_name, **log_extra
    )
