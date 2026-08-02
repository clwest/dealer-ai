"""Milestone 10 · Increment 7 (SESSION_112) — ComplianceRecord verbs.

Four verbs — one transactional write path + one targeted-update +
one pure read + one pure aggregate that powers the operator UI's
deal-jacket summary view.

- :func:`record_compliance` — transactional. Creates a
  :class:`ComplianceRecord` for a contract. Refuses cross-tenant
  contract at entry (:class:`CrossTenantComplianceError`).
  Refuses duplicate (Contract already has a ComplianceRecord via
  OneToOne — surfaced as
  :class:`ComplianceAlreadyExistsError`). Auto-populates
  ``retention_expires_at`` from
  ``contract.deal_structure.credit_application.retention_expires_at``
  for deal-jacket query-ability.
- :func:`update_compliance` — targeted update via
  ``.save(update_fields=...)``. Accepts any subset of the typed
  columns as keyword arguments; unspecified fields are
  preserved. Refuses unknown field names.
- :func:`get_compliance` — pure read, tenant-scoped by pk.
  Returns ``None`` for unknown / cross-tenant pk.
- :func:`deal_jacket_summary` — pure aggregate. Returns a dict
  suitable for the operator UI's per-deal compliance-audit
  view: ComplianceRecord fields + related Stipulation list +
  Chargeback list + Funding state + BEPA list. All in one
  read.

See ``docs/roadmap/MILESTONE_10_PLANNING.md`` §1.8 + §7 M10.7
for the contract.
"""

from __future__ import annotations

from typing import Optional

from django.db import IntegrityError, transaction

from ...models import (
    ComplianceRecord,
    Contract,
    Dealership,
)


# Whitelist of fields the update verb can touch. Keeps callers
# from silently setting fields the ComplianceRecord doesn't
# understand (typos in kwargs, misplaced attributes).
_UPDATABLE_FIELDS = frozenset(
    (
        "reg_z_disclosed_at",
        "ofac_checked_at",
        "ofac_hit",
        "red_flags_reviewed_at",
        "red_flags_notes",
        "privacy_notice_delivered_at",
        "safeguards_audit_at",
        "adverse_action_sent_at",
        "adverse_action_reason",
        "deal_jacket_url",
        "notes",
    )
)


class CrossTenantComplianceError(ValueError):
    """Raised when a ComplianceRecord verb is called with a
    ``dealership`` that does not match the parent contract's
    tenant.

    Subclasses :class:`ValueError`. Service-layer defense — the
    model layer's :meth:`ComplianceRecord.clean` is the second
    line.
    """


class ComplianceAlreadyExistsError(ValueError):
    """Raised when :func:`record_compliance` would violate the
    OneToOne constraint on :attr:`ComplianceRecord.contract`.

    Typed so the endpoint layer can map to HTTP 409 Conflict
    without string-matching. Matches
    :class:`services.f_and_i.FundingAlreadyExistsError` from
    M10.5.
    """


def _assert_same_tenant_contract(
    contract: Contract, dealership: Dealership
) -> None:
    if contract.dealership_id != dealership.pk:
        raise CrossTenantComplianceError(
            f"Contract #{contract.pk} belongs to "
            f"dealership_id={contract.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _derive_retention_expires_at(contract: Contract):
    """Return the retention window from the parent CreditApplication.

    Deal → DealStructure → CreditApplication is the FK path.
    Any link in the chain may be absent (unusual — signed
    contracts should have a full chain — but defensive). Returns
    ``None`` when the CreditApplication is missing or has NULL
    retention.
    """
    ds = getattr(contract, "deal_structure", None)
    if ds is None:
        return None
    ca = getattr(ds, "credit_application", None)
    if ca is None:
        return None
    return ca.retention_expires_at


@transaction.atomic
def record_compliance(
    *,
    dealership: Dealership,
    contract: Contract,
    deal_jacket_url: str = "",
    notes: str = "",
) -> ComplianceRecord:
    """Create a :class:`ComplianceRecord` for ``contract``.

    Refuses cross-tenant contract at entry
    (:class:`CrossTenantComplianceError`). Refuses if a
    ComplianceRecord already exists for the contract
    (:class:`ComplianceAlreadyExistsError`) — OneToOne invariant
    enforced at both service + DB layers.

    Auto-populates ``retention_expires_at`` from the parent
    :class:`CreditApplication` for deal-jacket query-ability.
    The CreditApplication's own retention clock remains the
    model-layer invariant per M10.1 §5.e — this denormalization
    just gives the operator UI a queryable retention field
    without traversing three FKs on every deal-jacket read.

    All typed compliance columns default to NULL/empty at
    create time. Populated via
    :func:`update_compliance` as operator actions occur.
    """
    _assert_same_tenant_contract(contract, dealership)

    try:
        return ComplianceRecord.objects.create(
            dealership=dealership,
            contract=contract,
            retention_expires_at=_derive_retention_expires_at(contract),
            deal_jacket_url=deal_jacket_url,
            notes=notes,
        )
    except IntegrityError as exc:
        raise ComplianceAlreadyExistsError(
            f"Contract #{contract.pk} already has a ComplianceRecord."
        ) from exc


def update_compliance(
    compliance: ComplianceRecord,
    **field_kwargs,
) -> ComplianceRecord:
    """Update any subset of the typed compliance columns.

    Refuses unknown field names (:class:`ValueError`) — protects
    against typos and misplaced kwargs. Unspecified fields are
    preserved.

    Uses targeted ``.save(update_fields=...)`` so untouched
    columns don't round-trip. ``updated_at`` is always included
    in the update.

    Returns the same :class:`ComplianceRecord` instance with
    the updated fields persisted.
    """
    unknown = set(field_kwargs) - _UPDATABLE_FIELDS
    if unknown:
        raise ValueError(
            f"Unknown field(s) for ComplianceRecord update: "
            f"{sorted(unknown)!r}. "
            f"Valid fields: {sorted(_UPDATABLE_FIELDS)!r}."
        )

    if not field_kwargs:
        # No-op update — return the instance unchanged.
        return compliance

    update_fields = list(field_kwargs.keys()) + ["updated_at"]
    for name, value in field_kwargs.items():
        setattr(compliance, name, value)

    compliance.save(update_fields=update_fields)
    return compliance


def get_compliance(
    pk: int, *, dealership: Dealership
) -> Optional[ComplianceRecord]:
    """Return the tenant-scoped :class:`ComplianceRecord` for
    ``pk``, or ``None`` if unknown / cross-tenant.

    Never raises. Never leaks existence.
    """
    return (
        ComplianceRecord.objects.filter(dealership=dealership, pk=pk)
        .select_related("contract")
        .first()
    )


def deal_jacket_summary(contract: Contract) -> dict:
    """Return a dict summary of the deal-jacket state for ``contract``.

    Pure aggregate. Never mutates. Powers the operator UI's per-
    deal compliance-audit view. Bundles:

    - ComplianceRecord fields (all NULL when no record exists yet).
    - Contract summary (state, contract_type, signed_at, voided_at).
    - Related Stipulation list (id, stip_type, state,
      cleared_at, evidence_url, documented_by_id).
    - Related Chargeback list (id, chargeback_type,
      chargeback_date, chargeback_amount).
    - Related Funding state (state, funded_at, funding_amount).
    - Related BEPA list (id, product_type, cost, retail_price,
      cancelled_at, cancellation_amount, product_agreement_url).

    All in one aggregate — the endpoint layer serializes to
    JSON. Tenant scoping is implicit via the contract argument
    (the endpoint verifies contract belongs to caller's
    dealership before invoking this verb).
    """
    compliance = getattr(contract, "compliance_record", None)
    funding = getattr(contract, "funding", None)

    # Deal-structure walk to find stipulations via lender
    # submissions. Contract → DealStructure → LenderSubmission →
    # Stipulation. Iterate to avoid a complex nested prefetch.
    stipulations = []
    for submission in contract.deal_structure.lender_submissions.all():
        for stip in submission.stipulations.all():
            stipulations.append(
                {
                    "id": stip.pk,
                    "lender_submission_id": stip.lender_submission_id,
                    "stip_type": stip.stip_type,
                    "state": stip.state,
                    "cleared_at": (
                        stip.cleared_at.isoformat()
                        if stip.cleared_at is not None
                        else None
                    ),
                    "documented_by_id": stip.documented_by_id,
                    "evidence_url": stip.evidence_url,
                    "notes": stip.notes,
                }
            )

    bepas = [
        {
            "id": bepa.pk,
            "product_type": bepa.product_type,
            "provider": bepa.provider,
            "cost": str(bepa.cost),
            "retail_price": str(bepa.retail_price),
            "cancelled_at": (
                bepa.cancelled_at.isoformat()
                if bepa.cancelled_at is not None
                else None
            ),
            "cancellation_amount": (
                str(bepa.cancellation_amount)
                if bepa.cancellation_amount is not None
                else None
            ),
            "product_agreement_url": bepa.product_agreement_url,
        }
        for bepa in contract.back_end_products.all()
    ]

    chargebacks = [
        {
            "id": cb.pk,
            "chargeback_type": cb.chargeback_type,
            "chargeback_date": cb.chargeback_date.isoformat(),
            "chargeback_amount": str(cb.chargeback_amount),
            "recorded_by_id": cb.recorded_by_id,
            "bepa_id": cb.bepa_id,
        }
        for cb in contract.chargebacks.all()
    ]

    return {
        "contract": {
            "id": contract.pk,
            "contract_type": contract.contract_type,
            "state": contract.state,
            "signed_at": (
                contract.signed_at.isoformat()
                if contract.signed_at is not None
                else None
            ),
            "voided_at": (
                contract.voided_at.isoformat()
                if contract.voided_at is not None
                else None
            ),
            "voided_reason": contract.voided_reason,
        },
        "compliance": (
            {
                "id": compliance.pk,
                "reg_z_disclosed_at": (
                    compliance.reg_z_disclosed_at.isoformat()
                    if compliance.reg_z_disclosed_at is not None
                    else None
                ),
                "ofac_checked_at": (
                    compliance.ofac_checked_at.isoformat()
                    if compliance.ofac_checked_at is not None
                    else None
                ),
                "ofac_hit": compliance.ofac_hit,
                "red_flags_reviewed_at": (
                    compliance.red_flags_reviewed_at.isoformat()
                    if compliance.red_flags_reviewed_at is not None
                    else None
                ),
                "red_flags_notes": compliance.red_flags_notes,
                "privacy_notice_delivered_at": (
                    compliance.privacy_notice_delivered_at.isoformat()
                    if compliance.privacy_notice_delivered_at is not None
                    else None
                ),
                "safeguards_audit_at": (
                    compliance.safeguards_audit_at.isoformat()
                    if compliance.safeguards_audit_at is not None
                    else None
                ),
                "adverse_action_sent_at": (
                    compliance.adverse_action_sent_at.isoformat()
                    if compliance.adverse_action_sent_at is not None
                    else None
                ),
                "adverse_action_reason": compliance.adverse_action_reason,
                "retention_expires_at": (
                    compliance.retention_expires_at.isoformat()
                    if compliance.retention_expires_at is not None
                    else None
                ),
                "deal_jacket_url": compliance.deal_jacket_url,
                "notes": compliance.notes,
            }
            if compliance is not None
            else None
        ),
        "funding": (
            {
                "id": funding.pk,
                "state": funding.state,
                "funded_at": (
                    funding.funded_at.isoformat()
                    if funding.funded_at is not None
                    else None
                ),
                "funding_amount": (
                    str(funding.funding_amount)
                    if funding.funding_amount is not None
                    else None
                ),
            }
            if funding is not None
            else None
        ),
        "stipulations": stipulations,
        "back_end_products": bepas,
        "chargebacks": chargebacks,
    }
