"""Milestone 13 · Increment 2 (SESSION_130) — M2 cost reconciliation.

Per MILESTONE_13_PLANNING.md §5 M13.2 + §0.a M13.2 decisions 1-6
(all as-recommended at SESSION_130 open):

- :func:`detect_unposted_costs` — pure query returning the unposted,
  non-estimate VehicleCost rows for one tenant. No writes.
- :func:`post_vehicle_cost_journal` — atomic sibling-service verb.
  Posts a two-line JournalEntry against the standard M13.2 mapping
  (DR 122000 Recon WIP / CR 200000 A/P Trade for positive amounts;
  swapped sides for negative-amount corrections per §0.a M13.2
  decision 5) and denormalizes ``posted_at`` on the source row.
- :func:`post_all_unposted_costs_for_dealership` — orchestrator.
  Iterates unposted rows for one tenant, posts each atomically,
  returns a summary.

**Uniform mapping.** Every eligible VehicleCost posts against the
same two accounts (§0.a M13.2 decision 2). Category-group-aware
mapping (flooring → floor-plan accounts, admin → rent / ad accounts,
etc.) defers to a later increment when operator evidence surfaces
the need. This preserves M13.1's fixed-vocab posture.

**Idempotency.** ``posted_at IS NULL AND is_estimate=False`` filter
gives cross-run idempotency naturally (§0.a M13.2 decision 6). A
row posted successfully has ``posted_at`` populated inside the same
``@transaction.atomic`` block that inserts the JournalEntry — either
both writes commit or neither does, so a partial state is impossible.
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ...models import Dealership, GLAccount, VehicleCost
from .journal import (
    CrossTenantGLAccountError,
    JournalLineInput,
    post_journal_entry,
)


_LOGGER = logging.getLogger("dealer_ai.accounting.vehicle_cost")


# Uniform GL mapping per §0.a M13.2 decision 2. Category-specific
# mappings defer to a later increment. Codes come from
# ``services.accounting.default_coa.DEFAULT_COA``.
RECON_WIP_ACCOUNT_CODE = "122000"
AP_TRADE_ACCOUNT_CODE = "200000"


class MissingDefaultAccountError(RuntimeError):
    """Raised when a required default COA account is missing for a tenant.

    Signals a broken invariant — the M13.1 migration seeded every
    Dealership with the full ``DEFAULT_COA``, and new Dealerships
    are expected to seed via
    :func:`services.accounting.seed_default_coa`. Fires only if
    operator activity has hidden one of the required accounts (via
    ``is_active=False``) or a deployment path bypassed the seeder.
    """


def detect_unposted_costs(
    *, dealership: Dealership
) -> QuerySet[VehicleCost]:
    """Return the unposted, non-estimate VehicleCost rows for a tenant.

    Pure query — no writes. Filter matches the detector's write
    filter so ``list(detect_unposted_costs(...))`` is the exact set
    the next :func:`post_all_unposted_costs_for_dealership` invocation
    will act on.

    Per §0.a M13.2 decisions 4 + 6:

    - Estimates (``is_estimate=True``) are excluded — projections that
      may change should not create GL noise.
    - ``posted_at__isnull=True`` gives cross-run idempotency. A
      previously-posted row is skipped without needing detector-side
      state.
    """
    return VehicleCost.objects.filter(
        dealership=dealership,
        posted_at__isnull=True,
        is_estimate=False,
    ).order_by("incurred_at", "id")


def _lookup_required_account(
    dealership: Dealership, code: str
) -> GLAccount:
    try:
        return GLAccount.objects.get(
            dealership=dealership, code=code, is_active=True
        )
    except GLAccount.DoesNotExist as exc:
        raise MissingDefaultAccountError(
            f"Required default COA account {code!r} missing (or "
            f"inactive) for dealership {dealership.slug!r}. Run "
            "services.accounting.seed_default_coa or re-activate "
            "the account before M13.2 posting will succeed."
        ) from exc


@transaction.atomic
def post_vehicle_cost_journal(
    *,
    dealership: Dealership,
    vehicle_cost: VehicleCost,
    posted_at: Optional[dt.datetime] = None,
) -> VehicleCost:
    """Post the GL journal entry for one VehicleCost row.

    Atomic — either the journal-entry insert AND the ``posted_at``
    denormalization commit, or neither does (§0.a M13.2 decision 6
    atomic-sibling-service posture per M12 §6 lesson 11).

    Refuses:

    - Cross-tenant VehicleCost
      (:class:`journal.CrossTenantJournalEntryError` via the account
      lookup — the row's dealership FK is used, so passing a
      mismatched ``dealership`` argument fails-closed at 404).
    - Missing default COA accounts
      (:class:`MissingDefaultAccountError` — signals a broken
      invariant, not a user error).

    Behavior per §0.a M13.2 decision 5 for negative-amount rows:

    - Positive ``amount`` → DR Recon WIP + CR A/P Trade.
    - Negative ``amount`` → DR A/P Trade + CR Recon WIP (reversal of
      typical direction). ``abs(amount)`` on both lines.

    Returns the refreshed VehicleCost instance with ``posted_at``
    populated.
    """
    if vehicle_cost.dealership_id != dealership.id:
        raise CrossTenantGLAccountError(
            f"VehicleCost {vehicle_cost.pk} belongs to another tenant."
        )

    recon_wip = _lookup_required_account(
        dealership, RECON_WIP_ACCOUNT_CODE
    )
    ap_trade = _lookup_required_account(
        dealership, AP_TRADE_ACCOUNT_CODE
    )

    magnitude = abs(vehicle_cost.amount)
    if vehicle_cost.amount >= Decimal("0.00"):
        debit_account = recon_wip
        credit_account = ap_trade
    else:
        debit_account = ap_trade
        credit_account = recon_wip

    effective = posted_at or timezone.now()
    stock_number = getattr(vehicle_cost.vehicle, "stock_number", "?")
    description = (
        f"M2 cost accrual — VehicleCost #{vehicle_cost.pk} "
        f"({vehicle_cost.get_category_display()}, stock {stock_number})"
    )
    line_memo = (
        f"VehicleCost #{vehicle_cost.pk}"
        + (f" ref {vehicle_cost.reference}" if vehicle_cost.reference else "")
    )

    post_journal_entry(
        dealership=dealership,
        description=description,
        posted_at=effective,
        lines=[
            JournalLineInput(
                account=debit_account,
                debit=magnitude,
                memo=line_memo,
            ),
            JournalLineInput(
                account=credit_account,
                credit=magnitude,
                memo=line_memo,
            ),
        ],
    )

    vehicle_cost.posted_at = effective
    vehicle_cost.save(update_fields=["posted_at", "updated_at"])
    return vehicle_cost


def post_all_unposted_costs_for_dealership(
    *,
    dealership: Dealership,
    now: Optional[dt.datetime] = None,
) -> dict[str, Any]:
    """Post every unposted VehicleCost for one tenant.

    Iterates :func:`detect_unposted_costs`. Each row is posted in
    its own :func:`post_vehicle_cost_journal` transaction — a failure
    on row N does not roll back rows 1..N-1 (progress is preserved).
    Failures are logged and counted in the returned dict.

    Returns a summary suitable for orchestrator logging + tests:
    ``{"dealership_id": ..., "dealership_slug": ..., "as_of": ...,
    "posted_count": ..., "failed_count": ..., "posted_ids": [...],
    "failed_ids": [...]}``.
    """
    effective = now or timezone.now()
    unposted = list(detect_unposted_costs(dealership=dealership))
    posted_ids: list[int] = []
    failed_ids: list[int] = []

    for cost in unposted:
        try:
            post_vehicle_cost_journal(
                dealership=dealership,
                vehicle_cost=cost,
                posted_at=effective,
            )
            posted_ids.append(cost.pk)
        except Exception:
            _LOGGER.exception(
                "accounting.vehicle_cost.post failed for VehicleCost pk=%s",
                cost.pk,
            )
            failed_ids.append(cost.pk)

    _LOGGER.info(
        "accounting.vehicle_cost.detector dealership=%s posted=%d failed=%d as_of=%s",
        dealership.slug,
        len(posted_ids),
        len(failed_ids),
        effective.isoformat(),
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": dealership.slug,
        "as_of": effective.isoformat(),
        "posted_count": len(posted_ids),
        "failed_count": len(failed_ids),
        "posted_ids": posted_ids,
        "failed_ids": failed_ids,
    }
