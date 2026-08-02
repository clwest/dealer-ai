"""Milestone 10 · Increment 5 (SESSION_110) — Contract + BackEndProductAgreement verbs.

Six verbs. Two lifecycle transitions (sign / void) + one write
path + one product-attach verb + two pure reads.

- :func:`record_contract` — transactional. Creates a
  :class:`Contract` for a deal structure in ``unsigned`` state.
  Refuses cross-tenant deal_structure
  (:class:`CrossTenantContractError`) and unknown contract_type
  (:class:`ValueError`).
- :func:`sign_contract` — state transition to ``signed``.
  Auto-populates ``signed_at`` (preserves the original signing
  moment on subsequent transitions). Refuses if the contract
  is already voided (voided contracts can't be signed —
  operators create a new Contract row instead).
- :func:`void_contract` — state transition to ``voided``.
  Auto-populates ``voided_at`` + operator-provided
  ``voided_reason``. Voiding preserves the audit trail per
  FINANCE §5.8 deal unwinds.
- :func:`record_back_end_product` — transactional. Attaches a
  :class:`BackEndProductAgreement` to a contract. Refuses
  cross-tenant contract and unknown product_type.
- :func:`get_contract` — pure read, tenant-scoped. Returns
  ``None`` for unknown / cross-tenant pk.
- :func:`list_products_for_contract` — pure read. FK filter.

Two-verb transition pattern (sign / void as distinct actions
rather than a generic state updater) matches how F&I actually
works — signing and voiding are distinct audit-trail moments,
not interchangeable transitions. This diverges from M10.3's
:func:`update_lender_submission_status` shape intentionally
because the auto-populated timestamps (``signed_at`` vs
``voided_at``) are semantically distinct.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.5 + §7 M10.5
for the contract.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ...models import (
    BEPA_TYPE_CHOICES,
    CONTRACT_STATE_SIGNED,
    CONTRACT_STATE_UNSIGNED,
    CONTRACT_STATE_VOIDED,
    CONTRACT_TYPE_CHOICES,
    BackEndProductAgreement,
    Contract,
    DealStructure,
    Dealership,
)


_VALID_CONTRACT_TYPES = frozenset(
    key for key, _ in CONTRACT_TYPE_CHOICES
)
_VALID_PRODUCT_TYPES = frozenset(key for key, _ in BEPA_TYPE_CHOICES)


class CrossTenantContractError(ValueError):
    """Raised when a Contract verb is called with a ``dealership``
    that does not match the parent deal_structure's or (for BEPA
    verbs) the parent contract's tenant.

    Subclasses :class:`ValueError`. Service-layer defense against
    cross-tenant writes — the model layer's :meth:`Contract.clean`
    / :meth:`BackEndProductAgreement.clean` are the second line.
    Belt + suspenders; do not remove either.
    """


class ContractAlreadyVoidedError(ValueError):
    """Raised when :func:`sign_contract` is called on a Contract
    already in ``voided`` state.

    Voided contracts can't be signed — operators create a new
    Contract row instead (per FINANCE §5.8 unwind pattern: the
    new contract is a distinct row, preserving the voided
    original for audit trail).

    Typed so the endpoint layer can map to HTTP 409 Conflict
    without string-matching.
    """


def _assert_same_tenant_deal_structure(
    deal: DealStructure, dealership: Dealership
) -> None:
    if deal.dealership_id != dealership.pk:
        raise CrossTenantContractError(
            f"DealStructure #{deal.pk} belongs to "
            f"dealership_id={deal.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_contract(
    contract: Contract, dealership: Dealership
) -> None:
    if contract.dealership_id != dealership.pk:
        raise CrossTenantContractError(
            f"Contract #{contract.pk} belongs to "
            f"dealership_id={contract.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_contract(
    *,
    dealership: Dealership,
    deal_structure: DealStructure,
    contract_type: str,
    signer_name: str = "",
    financed_amount: Decimal = Decimal("0.00"),
    total_of_payments: Decimal = Decimal("0.00"),
    finance_charge: Decimal = Decimal("0.00"),
    apr_disclosure: Decimal = Decimal("0.0000"),
    first_payment_date=None,
    notes: str = "",
) -> Contract:
    """Create a :class:`Contract` for ``deal_structure`` in the
    ``unsigned`` state.

    Refuses cross-tenant deal_structure at entry
    (:class:`CrossTenantContractError`). Refuses unknown
    ``contract_type`` values (:class:`ValueError`).

    Reg Z disclosure fields (``financed_amount``,
    ``total_of_payments``, ``finance_charge``, ``apr_disclosure``)
    are stored as-entered from the signed paper — the platform
    memorializes disclosure, it does not recompute. Defaults are
    zeros so cash contracts require no explicit financial fields.

    Transactional — the tenant check + insert run inside a
    single ``transaction.atomic`` block.
    """
    _assert_same_tenant_deal_structure(deal_structure, dealership)

    if contract_type not in _VALID_CONTRACT_TYPES:
        raise ValueError(
            f"Unknown contract_type={contract_type!r}. "
            f"Valid values: {sorted(_VALID_CONTRACT_TYPES)!r}."
        )

    return Contract.objects.create(
        dealership=dealership,
        deal_structure=deal_structure,
        contract_type=contract_type,
        state=CONTRACT_STATE_UNSIGNED,
        signer_name=signer_name,
        financed_amount=financed_amount,
        total_of_payments=total_of_payments,
        finance_charge=finance_charge,
        apr_disclosure=apr_disclosure,
        first_payment_date=first_payment_date,
        notes=notes,
    )


def sign_contract(
    contract: Contract,
    *,
    signer_name: Optional[str] = None,
    signed_at: Optional[datetime] = None,
) -> Contract:
    """Transition ``contract`` from ``unsigned`` (or any other
    state) to ``signed``. Auto-populates ``signed_at`` on the
    first transition and preserves it on subsequent transitions.

    Refuses if the contract is already ``voided``
    (:class:`ContractAlreadyVoidedError`) — per FINANCE §5.8
    unwind pattern, voided contracts require a new Contract
    row to re-sign against, preserving the voided original for
    audit trail.

    ``signer_name`` — when provided, updates the printed-name
    field. When omitted, preserves existing.

    Returns the same :class:`Contract` instance with updated
    fields persisted via targeted
    ``.save(update_fields=...)``.
    """
    if contract.state == CONTRACT_STATE_VOIDED:
        raise ContractAlreadyVoidedError(
            f"Contract #{contract.pk} is voided and cannot be signed. "
            f"Create a new Contract row to re-sign against."
        )

    update_fields = ["state", "updated_at"]
    contract.state = CONTRACT_STATE_SIGNED
    if contract.signed_at is None:
        contract.signed_at = signed_at if signed_at is not None else timezone.now()
        update_fields.append("signed_at")
    if signer_name is not None:
        contract.signer_name = signer_name
        update_fields.append("signer_name")

    contract.save(update_fields=update_fields)
    return contract


def void_contract(
    contract: Contract,
    *,
    voided_reason: str = "",
    voided_at: Optional[datetime] = None,
) -> Contract:
    """Transition ``contract`` to ``voided``. Auto-populates
    ``voided_at`` and records ``voided_reason`` (operator-
    provided rationale per FINANCE §5.8).

    No refusal — voiding is always allowed. A previously-signed
    contract that voids preserves ``signed_at`` (both moments
    are distinct historical events).

    Returns the same :class:`Contract` instance.
    """
    update_fields = ["state", "voided_at", "voided_reason", "updated_at"]
    contract.state = CONTRACT_STATE_VOIDED
    contract.voided_at = voided_at if voided_at is not None else timezone.now()
    contract.voided_reason = voided_reason
    contract.save(update_fields=update_fields)
    return contract


@transaction.atomic
def record_back_end_product(
    *,
    dealership: Dealership,
    contract: Contract,
    product_type: str,
    cost: Decimal,
    retail_price: Decimal,
    provider: str = "",
    term_months: Optional[int] = None,
    mileage_limit: Optional[int] = None,
    deductible: Optional[Decimal] = None,
    notes: str = "",
) -> BackEndProductAgreement:
    """Attach a :class:`BackEndProductAgreement` to ``contract``.

    Refuses cross-tenant contract at entry
    (:class:`CrossTenantContractError`). Refuses unknown
    ``product_type`` values (:class:`ValueError`).

    ``term_months`` / ``mileage_limit`` / ``deductible`` are
    optional per FINANCE §4.3-§4.5 — VSCs have all three; GAP
    has none; T&W has term_months only. Callers pass only the
    fields that apply to the product.

    Transactional.
    """
    _assert_same_tenant_contract(contract, dealership)

    if product_type not in _VALID_PRODUCT_TYPES:
        raise ValueError(
            f"Unknown product_type={product_type!r}. "
            f"Valid values: {sorted(_VALID_PRODUCT_TYPES)!r}."
        )

    return BackEndProductAgreement.objects.create(
        dealership=dealership,
        contract=contract,
        product_type=product_type,
        provider=provider,
        cost=cost,
        retail_price=retail_price,
        term_months=term_months,
        mileage_limit=mileage_limit,
        deductible=deductible,
        notes=notes,
    )


def get_contract(
    pk: int, *, dealership: Dealership
) -> Optional[Contract]:
    """Return the tenant-scoped :class:`Contract` for ``pk``,
    or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks existence.
    """
    return (
        Contract.objects.filter(dealership=dealership, pk=pk)
        .select_related("deal_structure")
        .first()
    )


def list_products_for_contract(
    contract: Contract,
) -> "QuerySet[BackEndProductAgreement]":
    """Return the ordered queryset of back-end product
    agreements for ``contract``.

    Pure verb. Ordering inherits from Meta (``-created_at``).
    """
    return BackEndProductAgreement.objects.filter(contract=contract)
