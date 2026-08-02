"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup service package.

Three verbs per ``MILESTONE_11_PLANNING.md`` §1.3 + §5.e Option A:

- :func:`record_deal_writeup` — create.
- :func:`approve_deal_writeup` — sales-manager approval.
- :func:`hand_off_to_fandi` — server-side auto-creates a matching
  M10.1 :class:`CreditApplication` via the existing
  :func:`services.f_and_i.record_credit_application` verb.

Domain errors:

- :class:`CrossTenantDealWriteupError` — 404 at endpoint layer
  (fail-closed).
- :class:`WriteupNotApprovedError` — 409 (state-machine violation:
  handoff requires prior approval).
- :class:`WriteupAlreadyHandedOffError` — 409 (idempotency: a single
  handoff per writeup avoids duplicate CreditApplication rows).
"""

from __future__ import annotations

from .deal_writeup import (
    CrossTenantDealWriteupError,
    WriteupAlreadyHandedOffError,
    WriteupNotApprovedError,
    approve_deal_writeup,
    hand_off_to_fandi,
    record_deal_writeup,
)

__all__ = [
    "CrossTenantDealWriteupError",
    "WriteupAlreadyHandedOffError",
    "WriteupNotApprovedError",
    "approve_deal_writeup",
    "hand_off_to_fandi",
    "record_deal_writeup",
]
