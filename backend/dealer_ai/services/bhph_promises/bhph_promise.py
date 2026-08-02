"""Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay verbs.

Three verbs per §7 M12.4 + §5.d Option A. Mirrors the M11.5 BeBack
service package shape (promised → kept / broken) with an added
:class:`BhphPayment` reference on the kept transition per §5.d.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from django.utils import timezone

from ...models import (
    BHPH_PROMISE_REASON_CHOICES,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    BHPH_PROMISE_STATE_PROMISED,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    Dealership,
)


_VALID_REASONS = {key for key, _ in BHPH_PROMISE_REASON_CHOICES}


class CrossTenantBhphPromiseError(Exception):
    """Raised when a promise write names a note or promise in another tenant."""


class UnknownReasonError(Exception):
    """Raised when ``promised_reason`` is not in the 3+1 vocab."""


class CrossPromisePaymentError(Exception):
    """Raised when the payment attached at mark_kept does not belong to
    the same tenant + the same note as the promise."""


class PromiseAlreadyTerminalError(Exception):
    """State-machine violation: promise already ``kept`` / ``broken``.

    Terminal states are final at M12.4. Silent re-transition would
    erase operator intent (was the promise marked kept, broken, or
    both?). Matches M11.5 BeBack posture — a future ``reopen`` verb
    can add the un-do path when operator UI surfaces the need.
    """


def record_promise(
    *,
    dealership: Dealership,
    note: BhphNote,
    promised_at: dt.datetime,
    promised_amount,
    promised_reason: str,
    notes: str = "",
) -> BhphPromiseToPay:
    """Persist a :class:`BhphPromiseToPay`.

    Refuses cross-tenant notes
    (:class:`CrossTenantBhphPromiseError`) and unknown reasons
    (:class:`UnknownReasonError`).
    """
    if note.dealership_id != dealership.id:
        raise CrossTenantBhphPromiseError(
            f"BhphNote {note.pk} belongs to another tenant."
        )
    if promised_reason not in _VALID_REASONS:
        raise UnknownReasonError(
            f"Unknown promised_reason={promised_reason!r}. "
            f"Valid reasons: {sorted(_VALID_REASONS)!r}."
        )
    return BhphPromiseToPay.objects.create(
        dealership=dealership,
        note=note,
        promised_at=promised_at,
        promised_amount=promised_amount,
        promised_reason=promised_reason,
        state=BHPH_PROMISE_STATE_PROMISED,
        notes=notes or "",
    )


def _assert_same_tenant(promise: BhphPromiseToPay, dealership: Dealership) -> None:
    if promise.dealership_id != dealership.id:
        raise CrossTenantBhphPromiseError(
            f"BhphPromiseToPay {promise.pk} belongs to another tenant."
        )


def mark_kept(
    *,
    dealership: Dealership,
    promise: BhphPromiseToPay,
    payment: BhphPayment,
    notes: str = "",
) -> BhphPromiseToPay:
    """promised → kept — operator-triggered reconciliation per §5.d.

    The operator identifies which :class:`BhphPayment` fulfilled the
    promise; this verb links the two. Refuses:

    - Cross-tenant promise (:class:`CrossTenantBhphPromiseError`).
    - Payment in another tenant OR against a different note
      (:class:`CrossPromisePaymentError`).
    - Already-terminal promise
      (:class:`PromiseAlreadyTerminalError`).
    """
    _assert_same_tenant(promise, dealership)
    if payment.dealership_id != dealership.id:
        raise CrossPromisePaymentError(
            f"BhphPayment {payment.pk} belongs to another tenant."
        )
    if payment.note_id != promise.note_id:
        raise CrossPromisePaymentError(
            f"BhphPayment {payment.pk} is against note "
            f"{payment.note_id}, not promise's note {promise.note_id}."
        )
    if promise.state != BHPH_PROMISE_STATE_PROMISED:
        raise PromiseAlreadyTerminalError(
            f"BhphPromiseToPay {promise.pk} is already in terminal "
            f"state {promise.state!r}. Re-transition refused."
        )
    promise.state = BHPH_PROMISE_STATE_KEPT
    promise.actual_payment = payment
    if notes:
        promise.notes = notes
    promise.save(
        update_fields=[
            "state",
            "actual_payment",
            "notes",
            "updated_at",
        ]
    )
    return promise


def mark_broken(
    *,
    dealership: Dealership,
    promise: BhphPromiseToPay,
    notes: str = "",
) -> BhphPromiseToPay:
    """promised → broken.

    Called by the M12.4 Celery detector when
    ``promised_at + grace_period`` passes without a reconciled
    payment. Also exposed as an operator-triggered endpoint.
    Never populates ``actual_payment`` — a broken promise has no
    fulfilling payment by definition.
    """
    _assert_same_tenant(promise, dealership)
    if promise.state != BHPH_PROMISE_STATE_PROMISED:
        raise PromiseAlreadyTerminalError(
            f"BhphPromiseToPay {promise.pk} is already in terminal "
            f"state {promise.state!r}. Re-transition refused."
        )
    promise.state = BHPH_PROMISE_STATE_BROKEN
    if notes:
        promise.notes = notes
    promise.save(update_fields=["state", "notes", "updated_at"])
    return promise
