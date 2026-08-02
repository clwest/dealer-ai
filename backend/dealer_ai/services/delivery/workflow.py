"""Milestone 9 · Increment 2 (SESSION_101) — Delivery write verbs.

Three verbs. All refuse cross-tenant access at entry.

- :func:`record_delivery` — write path. Creates a :class:`Delivery`
  for a :class:`Sale`. Refuses if the Sale already has a Delivery
  (OneToOne invariant enforced at both service + DB layers).
- :func:`update_checklist_item` — toggles a single checklist key.
  Refuses keys outside the M9.2 vocabulary
  (:class:`UnknownChecklistKeyError`).
- :func:`verify_insurance` — marks insurance verified. Writes both
  the denormalized ``insurance_verified`` column + the
  ``insurance_verified`` checklist key atomically.

Semantic decision — *the ``insurance_verified`` denormalized column
is the authoritative source*:

- Operator dashboards + compliance reports filter on the column
  (queryable, indexable), not the JSON key.
- :func:`verify_insurance` writes the column FIRST, then mirrors
  the key so an interrupted write leaves the two consistent (both
  False) rather than inconsistent (key True, column False).
- :func:`update_checklist_item` refuses to toggle
  ``insurance_verified`` directly — callers must use
  :func:`verify_insurance`. This keeps the audit trail
  (``insurance_verified_at``) meaningful.

See module ``dealer_ai.services.delivery`` for the facade.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ...models import (
    DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
    DELIVERY_CHECKLIST_KEYS,
    Delivery,
    Dealership,
    Sale,
    Vehicle,
    _default_delivery_checklist,
)


_VALID_CHECKLIST_KEYS = frozenset(DELIVERY_CHECKLIST_KEYS)


class CrossTenantDeliveryError(ValueError):
    """Raised when a Delivery verb is called with a ``dealership``
    that does not match the target :class:`Sale`'s tenant.

    Subclasses :class:`ValueError` so callers catching
    ``ValueError`` keep working. Service-layer defense against
    cross-tenant writes — the model layer's :meth:`Delivery.clean`
    is the second line.
    """


class DeliveryAlreadyExistsError(ValueError):
    """Raised when :func:`record_delivery` is called against a
    :class:`Sale` that already has a Delivery.

    The OneToOne constraint on ``Delivery.sale`` would raise
    :class:`django.db.utils.IntegrityError` at the DB layer; this
    service-level check surfaces the same invariant with a
    domain-specific error type so the endpoint layer can map it to
    HTTP 409 Conflict without string-matching a DB error message.
    """


class SaleNotFoundForDeliveryError(ValueError):
    """Raised when :func:`record_delivery` is called for a
    :class:`Vehicle` that has no :class:`Sale`.

    Distinct from "vehicle not found" — this is the workflow-order
    failure "you tried to create a Delivery before creating a
    Sale". The endpoint layer maps this to 409 Conflict rather
    than 404 to reflect that state.
    """


class UnknownChecklistKeyError(ValueError):
    """Raised when :func:`update_checklist_item` is called with a
    key outside the M9.2 checklist vocabulary
    (:data:`DELIVERY_CHECKLIST_KEYS`).

    Also raised when a caller attempts to toggle
    ``insurance_verified`` via :func:`update_checklist_item` — that
    key is reserved to :func:`verify_insurance` so the
    ``insurance_verified_at`` timestamp stays meaningful.
    """


def _assert_same_tenant_sale(sale: Sale, dealership: Dealership) -> None:
    if sale.dealership_id != dealership.pk:
        raise CrossTenantDeliveryError(
            f"Sale #{sale.pk} belongs to "
            f"dealership_id={sale.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


def _assert_same_tenant_delivery(
    delivery: Delivery, dealership: Dealership
) -> None:
    if delivery.dealership_id != dealership.pk:
        raise CrossTenantDeliveryError(
            f"Delivery #{delivery.pk} belongs to "
            f"dealership_id={delivery.dealership_id}, but the caller "
            f"passed dealership_id={dealership.pk}."
        )


@transaction.atomic
def record_delivery(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    delivery_date: Optional[date] = None,
    temp_tag_number: str = "",
    notes: str = "",
) -> Delivery:
    """Create a :class:`Delivery` for the :class:`Sale` associated
    with ``vehicle``.

    The Delivery row is created with every M9.2 checklist key set
    to False via :func:`_default_delivery_checklist`. Callers
    toggle items via :func:`update_checklist_item` and verify
    insurance via :func:`verify_insurance`.

    Refuses cross-tenant writes at entry
    (:class:`CrossTenantDeliveryError`). Refuses when the
    ``vehicle`` has no :class:`Sale`
    (:class:`SaleNotFoundForDeliveryError`). Refuses when the
    Sale already has a Delivery
    (:class:`DeliveryAlreadyExistsError`).

    Transactional — the Sale lookup + Delivery insert happen
    inside a single ``transaction.atomic`` block so a concurrent
    second ``record_delivery`` on the same Sale observes a
    serialized view of the OneToOne uniqueness invariant.

    ``delivery_date`` is nullable — the workflow may start before
    the delivery date is scheduled (e.g. "insurance verified
    today; delivery date TBD"). Callers set it later via
    ``PATCH /admin/deliveries/<id>/``.
    """
    # Vehicle tenancy is verified by the endpoint's tenant-scoped
    # lookup, but re-check the Sale tenant here so a service-level
    # caller (management command, admin action) can't bypass.
    try:
        sale = Sale.objects.select_related("dealership").get(vehicle=vehicle)
    except Sale.DoesNotExist:
        raise SaleNotFoundForDeliveryError(
            f"Vehicle #{vehicle.stock_number} has no Sale. Record a "
            f"Sale first via services.sale.record_sale."
        )

    _assert_same_tenant_sale(sale, dealership)

    if Delivery.objects.filter(sale=sale).exists():
        raise DeliveryAlreadyExistsError(
            f"Sale #{sale.pk} already has a Delivery."
        )

    return Delivery.objects.create(
        dealership=dealership,
        sale=sale,
        delivery_date=delivery_date,
        temp_tag_number=temp_tag_number,
        notes=notes,
    )


@transaction.atomic
def update_checklist_item(
    delivery: Delivery,
    *,
    dealership: Dealership,
    key: str,
    value: bool,
) -> Delivery:
    """Toggle a single checklist key on ``delivery``.

    Refuses keys outside :data:`DELIVERY_CHECKLIST_KEYS`
    (:class:`UnknownChecklistKeyError`). Refuses direct toggling
    of ``insurance_verified`` — that key must be written via
    :func:`verify_insurance` so the
    ``insurance_verified_at`` timestamp stays authoritative.

    Refuses cross-tenant writes at entry
    (:class:`CrossTenantDeliveryError`).

    Returns the refreshed :class:`Delivery` with the updated
    checklist.
    """
    _assert_same_tenant_delivery(delivery, dealership)

    if key not in _VALID_CHECKLIST_KEYS:
        raise UnknownChecklistKeyError(
            f"Unknown checklist key={key!r}. Valid keys: "
            f"{sorted(_VALID_CHECKLIST_KEYS)!r}."
        )
    if key == DELIVERY_CHECKLIST_INSURANCE_VERIFIED:
        raise UnknownChecklistKeyError(
            f"Cannot toggle {DELIVERY_CHECKLIST_INSURANCE_VERIFIED!r} "
            f"via update_checklist_item — use "
            f"services.delivery.verify_insurance so the "
            f"insurance_verified_at timestamp is set."
        )

    # Defensive: if a historical row was created before the M9.2
    # vocabulary landed, its checklist might be an empty dict.
    # Reset from defaults + overlay the caller's toggle.
    checklist = delivery.checklist or _default_delivery_checklist()
    checklist[key] = bool(value)
    delivery.checklist = checklist
    delivery.save(update_fields=["checklist", "updated_at"])
    delivery.refresh_from_db()
    return delivery


@transaction.atomic
def verify_insurance(
    delivery: Delivery,
    *,
    dealership: Dealership,
    at: Optional[datetime] = None,
) -> Delivery:
    """Mark insurance verified — writes both the column + the
    ``insurance_verified`` checklist key atomically.

    ``at`` defaults to :func:`django.utils.timezone.now` when
    omitted. Idempotent — calling twice does not shift the
    original ``insurance_verified_at`` (the first verification
    wins).

    Refuses cross-tenant writes at entry
    (:class:`CrossTenantDeliveryError`).
    """
    _assert_same_tenant_delivery(delivery, dealership)

    if delivery.insurance_verified:
        # Idempotent — keep the original timestamp + do not shift.
        # Return refreshed instance for symmetry with the update path.
        delivery.refresh_from_db()
        return delivery

    # Write column first, then mirror the key. If an exception
    # interrupts between the two writes the row is inconsistent, but
    # both writes happen inside the single ``@transaction.atomic``
    # decorator so partial persistence is impossible.
    delivery.insurance_verified = True
    delivery.insurance_verified_at = at or timezone.now()
    checklist = delivery.checklist or _default_delivery_checklist()
    checklist[DELIVERY_CHECKLIST_INSURANCE_VERIFIED] = True
    delivery.checklist = checklist
    delivery.save(
        update_fields=[
            "insurance_verified",
            "insurance_verified_at",
            "checklist",
            "updated_at",
        ]
    )
    delivery.refresh_from_db()
    return delivery
