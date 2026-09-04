"""SESSION_241 books-1 · acquisition posting.

Per ``TASK_books-1-acquisition-and-relief.md`` §1: buying a car debits
:code:`121000 Used Vehicle Inventory` and credits :code:`100000 Cash on
Hand` (or :code:`210000 Floor Plan Payable` when the acquisition is
floored). Today no acquisition is ever booked, and every sale credits
the car's whole cost out of Recon WIP — so RWIP shows negative and the
inventory account has never been touched. This module fixes the debit
side of the spine.

- :func:`post_acquisition_journal` — atomic sibling verb. Posts one
  balanced two-line entry against the acquisition's cost basis
  (purchase price + fees), sets ``VehicleAcquisition.posted_at``, and
  refuses to run twice for the same row.
- Signal binding lives in :func:`dealer_ai.apps.DealerAiConfig.ready`
  — every ``VehicleAcquisition.objects.create`` in a COA-seeded tenant
  posts its journal without the caller having to remember. Broken
  invariant tenants (test-only cases that skip
  :func:`services.accounting.seed_default_coa`) log a warning and skip
  the post so the fixture is not derailed; production tenants always
  have the COA (migration 0043).

Description in bookkeeper words per task §7: "Acquired #CC-081 — 2020
Chevrolet Silverado — auction". No milestone numbers on the lines this
verb writes.
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from ...models import Dealership, GLAccount, JournalEntry, VehicleAcquisition
from .journal import (
    CrossTenantGLAccountError,
    JournalLineInput,
    post_journal_entry,
)
from .vehicle_cost import MissingDefaultAccountError


_LOGGER = logging.getLogger("dealer_ai.accounting.acquisition")


USED_VEHICLE_INVENTORY_ACCOUNT_CODE = "121000"
CASH_ACCOUNT_CODE = "100000"
FLOOR_PLAN_PAYABLE_ACCOUNT_CODE = "210000"


def _lookup_required_account(dealership: Dealership, code: str) -> GLAccount:
    try:
        return GLAccount.objects.get(
            dealership=dealership, code=code, is_active=True
        )
    except GLAccount.DoesNotExist as exc:
        raise MissingDefaultAccountError(
            f"Required default COA account {code!r} missing (or "
            f"inactive) for dealership {dealership.slug!r}. Run "
            "services.accounting.seed_default_coa before booking "
            "acquisitions."
        ) from exc


def _acquisition_basis(acquisition: VehicleAcquisition) -> Decimal:
    """Return the full cost basis of the acquisition.

    Sums :attr:`purchase_price` plus every settlement fee that landed
    with the car (buyer / arbitration / transportation / title
    acquisition). Matches :func:`services.vehicle_ledger._acquisition_total`
    so the acquisition JE debits inventory for the same number the
    ledger read model reports as ``acquisition_total``.
    """
    return (
        acquisition.purchase_price
        + acquisition.buyer_fees
        + acquisition.arbitration_fees
        + acquisition.transportation_cost
        + acquisition.title_acquisition_cost
    )


def _acquired_description(acquisition: VehicleAcquisition) -> str:
    """Bookkeeper-shaped one-line description per task §7."""
    v = acquisition.vehicle
    year = getattr(v, "year", None)
    make = getattr(v, "make", "") or ""
    model = getattr(v, "model", "") or ""
    year_make_model = " ".join(
        str(part) for part in (year, make, model) if part
    ).strip()
    source_label = acquisition.get_source_display()
    stock = getattr(v, "stock_number", "?")
    if year_make_model:
        return f"Acquired #{stock} — {year_make_model} — {source_label}"
    return f"Acquired #{stock} — {source_label}"


@transaction.atomic
def post_acquisition_journal(
    *,
    dealership: Dealership,
    acquisition: VehicleAcquisition,
    posted_at: Optional[dt.datetime] = None,
    posted_by_user=None,
) -> Optional[JournalEntry]:
    """Post the DR inventory / CR cash-or-floor-plan journal for one acquisition.

    Atomic — either the JournalEntry AND the ``posted_at``
    denormalization on the acquisition commit, or nothing does.

    Refuses:

    - Cross-tenant acquisition
      (:class:`journal.CrossTenantGLAccountError`).
    - Missing / inactive default COA account
      (:class:`MissingDefaultAccountError`).

    Idempotent — returns ``None`` when ``acquisition.posted_at`` is
    already populated. Callers that want to force a repost should
    reverse the original entry via :func:`reverse_journal_entry`
    first; this verb never double-posts.

    Zero-basis acquisitions (`purchase_price + fees == 0`) skip the
    post and log a warning — a $0.00 acquisition would fail the
    :class:`InvalidJournalLineError` check inside :func:`post_journal_entry`
    and doesn't represent real bookkeeping activity anyway. This is
    the same posture :func:`post_sale_booking_journal` takes for
    zero-cost basis.
    """
    if acquisition.dealership_id != dealership.id:
        raise CrossTenantGLAccountError(
            f"VehicleAcquisition {acquisition.pk} belongs to another tenant."
        )
    if acquisition.posted_at is not None:
        return None

    basis = _acquisition_basis(acquisition)
    if basis <= Decimal("0.00"):
        _LOGGER.warning(
            "accounting.acquisition zero-basis dealership=%s "
            "acquisition_pk=%s stock=%s — post skipped.",
            dealership.slug,
            acquisition.pk,
            getattr(acquisition.vehicle, "stock_number", "?"),
        )
        return None

    inventory = _lookup_required_account(
        dealership, USED_VEHICLE_INVENTORY_ACCOUNT_CODE
    )
    credit_code = (
        FLOOR_PLAN_PAYABLE_ACCOUNT_CODE
        if acquisition.is_floored
        else CASH_ACCOUNT_CODE
    )
    credit_account = _lookup_required_account(dealership, credit_code)

    description = _acquired_description(acquisition)
    inventory_memo = "Vehicle into inventory"
    credit_memo = (
        "Floor plan draw" if acquisition.is_floored else "Cash paid at acquisition"
    )

    entry = post_journal_entry(
        dealership=dealership,
        description=description,
        posted_at=posted_at,
        posted_by_user=posted_by_user,
        lines=[
            JournalLineInput(
                account=inventory, debit=basis, memo=inventory_memo
            ),
            JournalLineInput(
                account=credit_account, credit=basis, memo=credit_memo
            ),
        ],
    )

    acquisition.posted_at = entry.posted_at
    acquisition.save(update_fields=["posted_at", "updated_at"])
    return entry


@receiver(post_save, sender=VehicleAcquisition, dispatch_uid="dealer_ai.books1.acquisition_post_save")
def _post_acquisition_on_create(sender, instance: VehicleAcquisition, created: bool, **kwargs) -> None:
    """post_save receiver: book the acquisition JE the moment the row lands.

    Fires only on ``created=True`` — updates never re-post (idempotency
    is also enforced inside :func:`post_acquisition_journal` via
    ``posted_at``). Silently skips when the tenant is missing the
    default COA — that's a broken-invariant condition in production
    but a common shape in older tests that predate M13.1. Production
    always has the COA seeded by migration 0043.
    """
    if not created:
        return
    if instance.posted_at is not None:
        return
    try:
        post_acquisition_journal(
            dealership=instance.dealership, acquisition=instance
        )
    except MissingDefaultAccountError:
        _LOGGER.warning(
            "accounting.acquisition post_save skipped for acquisition_pk=%s "
            "on dealership_slug=%s — COA missing. Seed via "
            "services.accounting.seed_default_coa before creating "
            "acquisitions in this tenant.",
            instance.pk,
            instance.dealership.slug,
        )


def register_acquisition_post_save() -> None:
    """No-op — the ``@receiver`` decorator above wires the signal at
    module import time. This helper exists so ``dealer_ai.apps`` can
    make the wiring explicit (matching the M1.3 tenancy autofill
    posture) and so the import happens inside ``AppConfig.ready``.
    """
    return None
