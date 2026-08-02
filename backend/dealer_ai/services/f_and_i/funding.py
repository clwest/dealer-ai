"""Milestone 10 · Increment 5 (SESSION_110) — Funding lifecycle verbs.

Three verbs. One transactional write path + one state-transition
updater + one pure read.

- :func:`record_funding` — transactional. Creates a
  :class:`Funding` row for a contract in ``pending_funding``
  state. Refuses cross-tenant contract at entry
  (:class:`CrossTenantFundingError`). Refuses if a Funding
  already exists for the contract (OneToOne invariant).
- :func:`mark_funded` — state transition to ``funded``.
  Auto-populates ``funded_at`` on the first transition
  (preserves on subsequent — the first-funded moment is the
  business fact). Records the actual ``funding_amount``.
- :func:`get_funding` — pure read, tenant-scoped. Returns
  ``None`` for unknown / cross-tenant pk.

Two-verb pattern (record / mark_funded as distinct actions)
matches the M10.5 Contract sign/void split — the auto-
populated timestamp is semantically the business fact, not an
arbitrary state-change side effect.

The ``chargedback`` state is included in the model vocabulary
at M10.5 but no verb transitions to it until M10.6 lands the
Chargeback entity (per §0.a resolution — vocabulary shipped
now to avoid a data migration at M10.6).

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.6 + §7 M10.5
for the contract.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from ...models import (
    FUNDING_STATE_FUNDED,
    FUNDING_STATE_PENDING,
    Contract,
    Dealership,
    Funding,
)


class CrossTenantFundingError(ValueError):
    """Raised when a Funding verb is called with a ``dealership``
    that does not match the parent contract's tenant.

    Subclasses :class:`ValueError`. Service-layer defense — the
    model layer's :meth:`Funding.clean` is the second line.
    """


class FundingAlreadyExistsError(ValueError):
    """Raised when :func:`record_funding` would violate the
    OneToOne constraint on :attr:`Funding.contract`.

    Typed so the endpoint layer can map to HTTP 409 Conflict
    without string-matching. Matches the
    :class:`services.sale.SaleAlreadyExistsError` pattern from
    M9.1 and :class:`services.f_and_i.DuplicateLenderProgramError`
    from M10.3.
    """


def _assert_same_tenant_contract(
    contract: Contract, dealership: Dealership
) -> None:
    if contract.dealership_id != dealership.pk:
        raise CrossTenantFundingError(
            f"Contract #{contract.pk} belongs to "
            f"dealership_id={contract.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_funding(
    *,
    dealership: Dealership,
    contract: Contract,
    submitted_to_lender_at: Optional[datetime] = None,
    notes: str = "",
) -> Funding:
    """Create a :class:`Funding` row for ``contract`` in the
    ``pending_funding`` state.

    Refuses cross-tenant contract at entry
    (:class:`CrossTenantFundingError`). Refuses if a Funding
    row already exists (:class:`FundingAlreadyExistsError`) —
    OneToOne invariant enforced at both service + DB layers.

    ``submitted_to_lender_at`` is operator-provided (the moment
    the funding packet was sent to the lender). Optional
    because some workflows record Funding earlier and update
    the submission timestamp on state transitions later.

    Transactional — tenant check + uniqueness check + insert
    happen inside a single ``transaction.atomic`` block so
    concurrent writes observe a serialized view of the
    OneToOne invariant.
    """
    _assert_same_tenant_contract(contract, dealership)

    try:
        return Funding.objects.create(
            dealership=dealership,
            contract=contract,
            state=FUNDING_STATE_PENDING,
            submitted_to_lender_at=submitted_to_lender_at,
            notes=notes,
        )
    except IntegrityError as exc:
        raise FundingAlreadyExistsError(
            f"Contract #{contract.pk} already has a Funding row."
        ) from exc


def mark_funded(
    funding: Funding,
    *,
    funding_amount: Decimal,
    funded_at: Optional[datetime] = None,
    notes: Optional[str] = None,
) -> Funding:
    """Transition ``funding`` to ``funded`` state and record the
    actual ``funding_amount``.

    Auto-populates ``funded_at`` on the first transition;
    preserves the existing timestamp on subsequent transitions
    (the first-funded moment is the business fact).

    ``funding_amount`` — always required (funded means the
    dealer knows the exact amount received). May differ from
    ``Contract.financed_amount`` due to lender discount fees
    per FINANCE §2.4.

    ``notes`` — when provided, replaces the existing notes;
    when omitted, preserved.

    Returns the same :class:`Funding` instance with updated
    fields persisted via targeted
    ``.save(update_fields=...)``.
    """
    update_fields = ["state", "funding_amount", "updated_at"]
    funding.state = FUNDING_STATE_FUNDED
    funding.funding_amount = funding_amount

    if funding.funded_at is None:
        funding.funded_at = funded_at if funded_at is not None else timezone.now()
        update_fields.append("funded_at")

    if notes is not None:
        funding.notes = notes
        update_fields.append("notes")

    funding.save(update_fields=update_fields)
    return funding


def get_funding(
    pk: int, *, dealership: Dealership
) -> Optional[Funding]:
    """Return the tenant-scoped :class:`Funding` for ``pk``, or
    ``None`` if unknown / cross-tenant.

    Never raises. Never leaks existence.
    """
    return (
        Funding.objects.filter(dealership=dealership, pk=pk)
        .select_related("contract")
        .first()
    )
