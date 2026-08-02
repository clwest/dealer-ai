"""Milestone 10 · Increment 6 (SESSION_111) — Chargeback + net_realized verbs.

Three verbs. One transactional write path (with two atomic side
effects) + one pure aggregate + one pure read.

- :func:`record_chargeback` — transactional. Creates a
  :class:`Chargeback` attached to a Contract and/or BEPA.
  Refuses cross-tenant parents at entry
  (:class:`CrossTenantChargebackError`). Refuses if neither
  parent is set (:class:`ValueError`). Refuses unknown
  ``chargeback_type`` values. Two side effects inside the same
  atomic block:

  1. When ``chargeback_type`` is one of the four deal-level
     types (see :data:`DEAL_LEVEL_CHARGEBACK_TYPES`) and the
     resolved Contract has a Funding row, auto-transitions the
     Funding to ``chargedback`` state per §1.7.f Option A.
     ``product_cancellation`` and ``other`` types are excluded
     (product cancellations reduce commission but leave the
     deal funded; ``other`` requires explicit operator
     PATCH).
  2. When ``chargeback_type=product_cancellation`` and the
     ``bepa`` FK is set, auto-populates
     ``BackEndProductAgreement.cancelled_at`` (from
     ``chargeback_date``) + ``cancellation_amount`` (from
     ``chargeback_amount``) per §1.7.c Option A.

  Optional ``skip_funding_transition=True`` kwarg for edge
  cases (partial reversal, operator override).

- :func:`net_realized` — pure aggregate. Returns
  ``sale.gross_realized - sum(chargeback amounts attributable
  to this sale's vehicle)`` per §5.c Option B (additive
  alongside M9.1 ``Sale.gross_realized``; no M9 schema change).
  Chargebacks are attributed via ``Contract → DealStructure →
  Vehicle`` match, unioned with BEPA-only chargebacks whose
  parent Contract targets the same Vehicle. Distinct pk set
  prevents double-counting when both FKs point to matching
  parents.

- :func:`get_chargeback` — pure read, tenant-scoped by pk.
  Returns ``None`` for unknown / cross-tenant pk.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.7 + §5.c + §7
M10.6 for the contract.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from ...models import (
    BackEndProductAgreement,
    CHARGEBACK_TYPE_CHOICES,
    CHARGEBACK_TYPE_PRODUCT_CANCELLATION,
    Chargeback,
    Contract,
    DEAL_LEVEL_CHARGEBACK_TYPES,
    Dealership,
    FUNDING_STATE_CHARGEDBACK,
    Sale,
)


_VALID_TYPES = frozenset(key for key, _ in CHARGEBACK_TYPE_CHOICES)


class CrossTenantChargebackError(ValueError):
    """Raised when a Chargeback verb is called with a
    ``dealership`` that does not match the parent contract's or
    BEPA's tenant.

    Subclasses :class:`ValueError`. Service-layer defense — the
    model layer's :meth:`Chargeback.clean` is the second line.
    """


def _assert_same_tenant_contract(
    contract: Contract, dealership: Dealership
) -> None:
    if contract.dealership_id != dealership.pk:
        raise CrossTenantChargebackError(
            f"Contract #{contract.pk} belongs to "
            f"dealership_id={contract.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_bepa(
    bepa: BackEndProductAgreement, dealership: Dealership
) -> None:
    if bepa.dealership_id != dealership.pk:
        raise CrossTenantChargebackError(
            f"BackEndProductAgreement #{bepa.pk} belongs to "
            f"dealership_id={bepa.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _resolve_effective_contract(
    contract: Optional[Contract],
    bepa: Optional[BackEndProductAgreement],
) -> Optional[Contract]:
    """Return the Contract for the Funding side-effect lookup.

    Prefers the direct ``contract`` FK; falls back to
    ``bepa.contract`` when only ``bepa`` is set. Returns
    ``None`` when neither is available (shouldn't happen since
    the caller enforces at-least-one, but defensive).
    """
    if contract is not None:
        return contract
    if bepa is not None:
        return bepa.contract
    return None


@transaction.atomic
def record_chargeback(
    *,
    dealership: Dealership,
    chargeback_type: str,
    chargeback_date: date,
    chargeback_amount: Decimal,
    contract: Optional[Contract] = None,
    bepa: Optional[BackEndProductAgreement] = None,
    recorded_by=None,
    notes: str = "",
    skip_funding_transition: bool = False,
) -> Chargeback:
    """Create a :class:`Chargeback` for a Contract and/or BEPA.

    Refuses if neither ``contract`` nor ``bepa`` is set
    (:class:`ValueError`) — §1.7.a Option A requires at least one
    parent. Refuses cross-tenant parents at entry
    (:class:`CrossTenantChargebackError`). Refuses unknown
    ``chargeback_type`` values.

    **Two atomic side effects:**

    1. **Funding auto-transition** (per §1.7.f Option A). When
       ``chargeback_type`` is one of :data:`DEAL_LEVEL_CHARGEBACK_TYPES`
       and the resolved Contract has a Funding row, the Funding
       transitions to ``chargedback`` state within the same
       transaction. ``skip_funding_transition=True`` bypasses
       this for edge cases (partial reversal, operator
       override, novel-type recovery scenarios).

    2. **BEPA cancellation-field auto-populate** (per §1.7.c
       Option A). When
       ``chargeback_type=product_cancellation`` and ``bepa``
       is set, populates ``bepa.cancelled_at`` +
       ``bepa.cancellation_amount``. Persisted via targeted
       ``.save(update_fields=...)``.

    Transactional — all three actions (Chargeback insert +
    optional Funding update + optional BEPA update) run inside
    a single ``transaction.atomic`` block. A failure in any
    step reverts all writes.
    """
    if contract is None and bepa is None:
        raise ValueError(
            "Chargeback must attach to at least one of contract or "
            "bepa (see MILESTONE_10_PLANNING.md §1.7.a Option A)."
        )
    if contract is not None:
        _assert_same_tenant_contract(contract, dealership)
    if bepa is not None:
        _assert_same_tenant_bepa(bepa, dealership)

    if chargeback_type not in _VALID_TYPES:
        raise ValueError(
            f"Unknown chargeback_type={chargeback_type!r}. "
            f"Valid values: {sorted(_VALID_TYPES)!r}."
        )

    chargeback = Chargeback.objects.create(
        dealership=dealership,
        contract=contract,
        bepa=bepa,
        chargeback_type=chargeback_type,
        chargeback_date=chargeback_date,
        chargeback_amount=chargeback_amount,
        recorded_by=recorded_by,
        notes=notes,
    )

    # Side effect 1: Funding auto-transition for deal-level types.
    if (
        chargeback_type in DEAL_LEVEL_CHARGEBACK_TYPES
        and not skip_funding_transition
    ):
        effective_contract = _resolve_effective_contract(contract, bepa)
        if effective_contract is not None:
            # Funding is OneToOne — .funding is None or a Funding row.
            funding = getattr(effective_contract, "funding", None)
            if funding is not None:
                funding.state = FUNDING_STATE_CHARGEDBACK
                funding.save(update_fields=["state", "updated_at"])

    # Side effect 2: BEPA cancellation-field auto-populate. Use
    # the operator-provided ``chargeback_date`` (business date) at
    # start-of-day so downstream "when was this cancelled"
    # date filters match the chargeback event's business date
    # rather than the row insert timestamp.
    if (
        chargeback_type == CHARGEBACK_TYPE_PRODUCT_CANCELLATION
        and bepa is not None
    ):
        naive_dt = datetime.combine(chargeback_date, time.min)
        aware_dt = (
            timezone.make_aware(naive_dt)
            if timezone.is_naive(naive_dt)
            else naive_dt
        )
        bepa.cancelled_at = aware_dt
        bepa.cancellation_amount = chargeback_amount
        bepa.save(
            update_fields=["cancelled_at", "cancellation_amount", "updated_at"]
        )

    return chargeback


def net_realized(sale: Sale) -> Decimal:
    """Return ``sale.gross_realized - sum(chargebacks)``.

    Pure aggregate. Never mutates. Per §5.c Option B (SESSION_106):
    additive alongside M9.1 ``Sale.gross_realized``; no M9 schema
    change.

    Attribution paths:

    1. **Direct Contract FK.** Any Chargeback whose
       ``contract.deal_structure.vehicle`` matches the sale's
       Vehicle.
    2. **BEPA-only.** Any Chargeback with ``contract=None`` and
       ``bepa.contract.deal_structure.vehicle`` matches.

    Both paths unioned via ``Q()``, then deduped by pk to avoid
    double-counting product-cancellation chargebacks that have
    both FKs pointing to matching parents.

    Returns a Decimal. When no chargebacks exist for this sale's
    vehicle, equals ``sale.gross_realized``.
    """
    # Q() union catches both direct and BEPA-mediated attribution.
    # ``distinct()`` alone can produce query-plan ambiguity across
    # DB backends when JOINs are involved; extract the pk set
    # first, then aggregate on that concrete set.
    chargeback_pks = set(
        Chargeback.objects.filter(
            Q(contract__deal_structure__vehicle=sale.vehicle)
            | Q(bepa__contract__deal_structure__vehicle=sale.vehicle),
            dealership=sale.dealership,
        ).values_list("pk", flat=True)
    )
    if not chargeback_pks:
        return sale.gross_realized

    total = (
        Chargeback.objects.filter(pk__in=chargeback_pks).aggregate(
            s=Sum("chargeback_amount")
        )["s"]
        or Decimal("0.00")
    )
    return sale.gross_realized - total


def get_chargeback(
    pk: int, *, dealership: Dealership
) -> Optional[Chargeback]:
    """Return the tenant-scoped :class:`Chargeback` for ``pk``,
    or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks existence.
    """
    return (
        Chargeback.objects.filter(dealership=dealership, pk=pk)
        .select_related("contract", "bepa", "recorded_by")
        .first()
    )
