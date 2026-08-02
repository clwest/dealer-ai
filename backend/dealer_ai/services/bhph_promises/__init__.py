"""Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay service package.

Three verbs per ``MILESTONE_12_PLANNING.md`` §7 M12.4 + §5.d Option A
(locked at SESSION_121 open — operator-triggered reconciliation):

- :func:`record_promise` — customer promises to pay.
- :func:`mark_kept` — promised → kept (operator-triggered per §5.d).
  Requires a :class:`BhphPayment` reference for the reconciliation.
- :func:`mark_broken` — promised → broken. Called by the M12.4
  Celery detector when the grace period elapses, also exposed as
  an operator-triggered endpoint.

Domain errors:

- :class:`CrossTenantBhphPromiseError` — 404 at endpoint layer.
- :class:`UnknownReasonError` — 400 (reason not in the 3+1 vocab).
- :class:`CrossPromisePaymentError` — 400 (payment attached at
  ``mark_kept`` must belong to the same tenant + same note).
- :class:`PromiseAlreadyTerminalError` — 409 (state-machine
  violation; terminal states are final).
"""

from __future__ import annotations

from .bhph_promise import (
    CrossPromisePaymentError,
    CrossTenantBhphPromiseError,
    PromiseAlreadyTerminalError,
    UnknownReasonError,
    mark_broken,
    mark_kept,
    record_promise,
)
from .tasks import (
    detect_broken_promises_for_all_tenants,
    detect_broken_promises_for_dealership,
)

__all__ = [
    "CrossPromisePaymentError",
    "CrossTenantBhphPromiseError",
    "PromiseAlreadyTerminalError",
    "UnknownReasonError",
    "detect_broken_promises_for_all_tenants",
    "detect_broken_promises_for_dealership",
    "mark_broken",
    "mark_kept",
    "record_promise",
]
