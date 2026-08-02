"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote write + read verbs.

Three verbs per §7 M12.1 + §5.a Option A. See package ``__init__`` for
the domain-error → HTTP mapping contract.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Optional

from ...models import (
    BHPH_PAYMENT_FREQUENCY_CHOICES,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
)
from ..payment_engine import (
    UnknownBhphFrequencyError,
    bhph_note_periodic_payment,
    bhph_note_schedule,
)


_VALID_FREQUENCIES = {key for key, _ in BHPH_PAYMENT_FREQUENCY_CHOICES}


class NonBhphSaleError(Exception):
    """Sale exists but ``finance_type != "bhph"``.

    Belt (model ``clean()``) + suspenders (this service verb). Raised
    with a 400 mapping at the endpoint layer since it represents a
    caller-supplied input mismatch (not a fail-closed lookup miss).
    """


class CrossTenantBhphNoteError(Exception):
    """Raised when a BhphNote write names a Sale in another tenant."""


class DuplicateBhphNoteError(Exception):
    """Raised when a BhphNote already exists for the target Sale.

    The OneToOne field would raise ``IntegrityError`` on write; this
    service verb checks first so the caller gets a clean 409 instead
    of a DB-level exception surfacing at the endpoint layer.
    """


def record_bhph_note(
    *,
    dealership: Dealership,
    sale: Sale,
    principal_financed: Decimal,
    apr: Decimal,
    term_weeks: int,
    payment_frequency: str,
    first_payment_due: dt.date,
    default_grace_days: int = 5,
) -> BhphNote:
    """Originate a BhphNote against a BHPH Sale.

    Computes ``payment_amount`` from the loan terms via the pure
    :func:`services.payment_engine.bhph_note_periodic_payment` verb
    and persists the row. Refuses:

    - Cross-tenant Sale (:class:`CrossTenantBhphNoteError` — 404).
    - Non-BHPH Sale (:class:`NonBhphSaleError` — 400).
    - Duplicate note per Sale (:class:`DuplicateBhphNoteError` — 409).
    - Unknown ``payment_frequency`` (:class:`UnknownBhphFrequencyError`
      → 400).
    """
    if sale.dealership_id != dealership.id:
        raise CrossTenantBhphNoteError(
            f"Sale {sale.pk} belongs to another tenant."
        )
    if sale.finance_type != SALE_FINANCE_TYPE_BHPH:
        raise NonBhphSaleError(
            f"Sale {sale.pk} has finance_type={sale.finance_type!r}; "
            "BhphNote origination requires 'bhph'."
        )
    if payment_frequency not in _VALID_FREQUENCIES:
        raise UnknownBhphFrequencyError(
            f"Unknown payment_frequency={payment_frequency!r}. "
            f"Valid: {sorted(_VALID_FREQUENCIES)!r}."
        )
    if BhphNote.objects.filter(sale=sale).exists():
        raise DuplicateBhphNoteError(
            f"BhphNote already exists for Sale {sale.pk}. One note per "
            "Sale (M12.1 §5.a schema invariant)."
        )

    principal_dec = _as_decimal(principal_financed)
    apr_dec = _as_decimal(apr)
    payment_amount = bhph_note_periodic_payment(
        principal_dec, apr_dec, term_weeks, payment_frequency  # type: ignore[arg-type]
    )

    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=principal_dec,
        apr=apr_dec,
        term_weeks=term_weeks,
        payment_frequency=payment_frequency,
        payment_amount=payment_amount,
        first_payment_due=first_payment_due,
        default_grace_days=default_grace_days,
    )


def get_bhph_note(
    *, pk: int, dealership: Dealership
) -> Optional[BhphNote]:
    """Tenant-scoped BhphNote read.

    Returns ``None`` when the pk doesn't exist or belongs to another
    tenant (fail-closed — the endpoint layer maps to 404).
    """
    try:
        return BhphNote.objects.get(pk=pk, dealership=dealership)
    except BhphNote.DoesNotExist:
        return None


def get_payment_schedule(note: BhphNote) -> list[tuple[dt.date, Decimal]]:
    """Compute the full payment schedule for a BhphNote.

    Pure verb. No DB writes. Returns
    ``[(due_date_1, amount), (due_date_2, amount), ...]`` where each
    amount equals the note's ``payment_amount``. The per-payment
    entity that persists individual intakes lands at M12.2.
    """
    return bhph_note_schedule(
        note.principal_financed,
        note.apr,
        note.term_weeks,
        note.payment_frequency,  # type: ignore[arg-type]
        note.first_payment_due,
    )


def _as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
