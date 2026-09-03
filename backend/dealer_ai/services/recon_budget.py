"""SESSION_228 — per-store recon budget with an exception queue.

The recon-spend authorization gate has two shapes now:

- ``per_job`` (today's behaviour) — every WorkOrder waits on a human.
  ``authorize_or_queue`` leaves it in ``draft``; the manager clicks
  Authorize to move it to ``approved``.
- ``budget`` — the store sets a per-car recon number. Under budget:
  the WO auto-authorizes with a "auto-authorized: under store recon
  budget ($X of $B)" note. Over budget: the WO lands in a
  cross-lot Needs-authorization queue for a manager to review with
  three exits (authorize-with-override, cancel, send-to-wholesale).

Reads the mode + budget from the dealership's onboarding profile
(``DealerOnboardingProfile``). Existing stores keep ``per_job`` so
nothing changes for anyone until the store flips it.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Sum

from ..models import (
    ConditionFinding,
    Dealership,
    DealerOnboardingProfile,
    ReconRateCard,
    Vehicle,
    VehicleReconBudgetOverride,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WorkOrder,
)
from . import recon as recon_service

_ZERO = Decimal("0.00")
_CENTS = Decimal("0.01")

# SESSION_229 Part 4 — the queued note was surviving override
# authorization, so an Approved chip and an amber "needs
# authorization" note appeared on the same card. Strip the note in
# the override path (backend, so the stored note stops lying too).
# Matches the exact prefix written by ``authorize_or_queue``:
# "needs authorization: $X over the $Y cap. "
_QUEUED_NOTE_PREFIX_RE = re.compile(
    r"^needs authorization: \$[\d.,]+ over the \$[\d.,]+ cap\.\s*"
)


def strip_queued_note_prefix(notes: str) -> str:
    """Remove the ``needs authorization: ...`` prefix written by
    :func:`authorize_or_queue`. Leaves the operator's own notes
    untouched."""
    return _QUEUED_NOTE_PREFIX_RE.sub("", notes or "", count=1)


def _q(value: Decimal) -> Decimal:
    """Quantize a Decimal to two places. SESSION_229 Part 3 fixes
    the shape at the source so ``recon_budget`` and ``recon_spend``
    stop drifting from ``"1200.00"`` to ``"1644"`` after an
    override."""
    return value.quantize(_CENTS)

# Statuses that count against the per-car budget on the estimate
# side (labor + parts). Cancelled WOs do not contribute; completed
# WOs contribute via their actual, not their estimate.
_BUDGET_ESTIMATE_STATUSES = frozenset(
    {
        WORK_ORDER_STATUS_DRAFT,
        WORK_ORDER_STATUS_APPROVED,
        WORK_ORDER_STATUS_IN_PROGRESS,
    }
)


# ---- Domain errors --------------------------------------------------------


class BudgetCheckError(ValueError):
    """Raised by ``authorize_or_queue`` when preconditions fail
    (e.g. the WO has no linked findings — the recon-service invariant
    that gates ``approve_work_order`` is enforced here too so a queued
    WO can never be one Authorize click away from a 409)."""


# ---- Store settings -------------------------------------------------------


def _store_profile(dealership: Dealership) -> Optional[DealerOnboardingProfile]:
    """Return the singleton :class:`DealerOnboardingProfile` for the
    dealership, or ``None`` when no profile row exists (a fresh
    tenant that has not opened the onboarding page yet).

    The onboarding profile is legally many-per-Dealership at the
    schema layer (SESSION_037 note), but the view layer treats it as
    a singleton — same convention followed here: read the most
    recently updated row."""
    return (
        DealerOnboardingProfile.objects.filter(dealership=dealership)
        .order_by("-updated_at")
        .first()
    )


def authorization_mode(dealership: Dealership) -> str:
    """Return the store's recon authorization mode. Defaults to
    ``per_job`` when no profile row exists so existing stores keep
    today's behaviour."""
    profile = _store_profile(dealership)
    if profile is None:
        return DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_PER_JOB
    return profile.recon_authorization_mode


# ---- Budget for a car -----------------------------------------------------


def _band_basis_for(vehicle: Vehicle) -> Decimal:
    """Return the amount bands are keyed against for ``vehicle``.

    Chris's framing (and the SESSION_228.1 review): bands are by
    acquisition COST, not by asking price. A car acquired for
    $6,802 lives in band 1 whether it is later priced at $8k or
    $12k. Uses ``vehicle.acquisition_total`` (sum of every cash
    line on the acquisition row — purchase price + fees +
    transportation + title). Falls back to ``vehicle.price`` only
    when the car has no acquisition record yet — every fresh trade
    has an acquisition record within seconds, but the fallback keeps
    the check working during the narrow window between Vehicle
    create and VehicleAcquisition create.
    """
    total = getattr(vehicle, "acquisition_total", None)
    if total and Decimal(total) > Decimal("0"):
        return Decimal(total)
    return Decimal(str(getattr(vehicle, "price", None) or "0"))


def _base_budget_from_bands(
    profile: DealerOnboardingProfile, vehicle: Vehicle
) -> Optional[Decimal]:
    """Pick the band whose ``up_to`` covers the vehicle's acquisition
    total (see :func:`_band_basis_for`), else fall back to
    ``recon_budget_default``. Returns ``None`` when neither is set
    (store has budget mode on but hasn't filled in a number —
    treated as "no cap"; ``authorize_or_queue`` then acts like
    ``per_job``)."""
    bands = list(profile.recon_budget_bands or [])
    # Sort bands by up_to; None (catch-all) comes last.
    def _band_key(b):
        up_to = b.get("up_to")
        if up_to is None:
            return (1, Decimal("0"))
        return (0, Decimal(str(up_to)))

    basis = _band_basis_for(vehicle)
    for band in sorted(bands, key=_band_key):
        up_to = band.get("up_to")
        if up_to is None or basis <= Decimal(str(up_to)):
            budget = band.get("budget")
            if budget is not None:
                return Decimal(str(budget))
            break
    return profile.recon_budget_default


def recon_budget_for(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[Decimal]:
    """Return the effective recon budget for ``vehicle`` — bands →
    default → plus SUM of overrides granted on this car. Returns
    ``None`` when the store has no budget cap in effect (per_job
    stores, or budget stores with nothing filled in)."""
    profile = _store_profile(dealership)
    if profile is None:
        return None
    if (
        profile.recon_authorization_mode
        != DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_BUDGET
    ):
        return None
    base = _base_budget_from_bands(profile, vehicle)
    if base is None:
        return None
    override_sum = (
        VehicleReconBudgetOverride.objects.filter(vehicle=vehicle)
        .aggregate(total=Sum("amount"))
        .get("total")
    ) or _ZERO
    return _q(Decimal(base) + Decimal(override_sum))


# ---- Spend on a car -------------------------------------------------------


def _wo_estimate_total(wo: WorkOrder) -> Decimal:
    """Labor (``estimated_cost`` or ``authorized_cost`` if it was
    tightened at approve time) + parts (unit_cost × qty for
    non-returned parts). SESSION_228 Part 1b: parts count against
    the budget."""
    labor = wo.authorized_cost or wo.estimated_cost or _ZERO
    parts = _parts_estimate(wo)
    return Decimal(labor) + parts


def _wo_actual_total(wo: WorkOrder) -> Decimal:
    labor = wo.actual_cost or _ZERO
    parts = _parts_actual(wo)
    return Decimal(labor) + parts


def _parts_estimate(wo: WorkOrder) -> Decimal:
    """Parts that count against the estimate — everything except
    ``returned``. ``needed`` / ``ordered`` / ``backordered`` /
    ``received`` / ``installed`` all count; a returned part is a
    reversal."""
    total = _ZERO
    for p in wo.parts.all():
        if p.status == "returned" or p.unit_cost is None:
            continue
        total += Decimal(p.unit_cost) * Decimal(p.quantity or 1)
    return total


def _parts_actual(wo: WorkOrder) -> Decimal:
    total = _ZERO
    for p in wo.parts.all():
        if p.status != "installed" or p.unit_cost is None:
            continue
        total += Decimal(p.unit_cost) * Decimal(p.quantity or 1)
    return total


def recon_spend_for(
    vehicle: Vehicle, *, dealership: Dealership, exclude_wo: Optional[WorkOrder] = None
) -> Decimal:
    """Return the money already committed to recon on ``vehicle``:

    - Every live WO (draft / approved / in_progress) counts its
      estimate total (labor + parts).
    - Every completed WO counts its actual total.
    - Cancelled WOs contribute zero.

    Pass ``exclude_wo=`` to exclude a specific WO from the sum —
    used by ``authorize_or_queue`` so a WO checks whether IT would
    push the car over, not whether it already has (double-counting
    itself).
    """
    total = _ZERO
    qs = WorkOrder.objects.filter(
        vehicle=vehicle, dealership=dealership
    ).prefetch_related("parts")
    if exclude_wo is not None:
        qs = qs.exclude(pk=exclude_wo.pk)
    for wo in qs:
        if wo.status in _BUDGET_ESTIMATE_STATUSES:
            total += _wo_estimate_total(wo)
        elif wo.status == WORK_ORDER_STATUS_COMPLETED:
            total += _wo_actual_total(wo)
        # cancelled: contributes zero
    return _q(total)


# ---- Public totals ------------------------------------------------------


def wo_estimate_total(wo: WorkOrder) -> Decimal:
    """Labor + parts on the estimate side. Public so views can render
    the number the same way the budget check reads it."""
    return _wo_estimate_total(wo)


def wo_actual_total(wo: WorkOrder) -> Decimal:
    """Labor + parts on the actual side. Public for the same reason
    as :func:`wo_estimate_total`."""
    return _wo_actual_total(wo)


def parts_estimate(wo: WorkOrder) -> Decimal:
    return _parts_estimate(wo)


def parts_actual(wo: WorkOrder) -> Decimal:
    return _parts_actual(wo)


# ---- Authorize or queue ---------------------------------------------------


def authorize_or_queue(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    actor=None,
) -> tuple[WorkOrder, bool]:
    """Decide whether ``work_order`` auto-authorizes under the store's
    recon budget, or stays in draft for a human to authorize.

    Returns ``(work_order, auto_authorized)`` — the boolean is
    ``True`` when the WO was moved to ``approved`` under budget.

    ``per_job`` stores: always returns ``(wo, False)`` — the WO
    stays in draft. Callers rely on this to preserve existing
    behaviour byte-for-byte.

    ``budget`` stores: computes the car's total spend WITH this WO
    included; if <= budget, calls the recon service's
    ``approve_work_order`` and adds a note "auto-authorized: under
    store recon budget ($X of $B)". If over, leaves the WO in
    draft — it will show up on the cross-lot Needs-authorization
    queue with the overage.
    """
    mode = authorization_mode(dealership)
    if mode == DealerOnboardingProfile.RECON_AUTHORIZATION_MODE_PER_JOB:
        return work_order, False

    # Budget mode — read the cap for this car. If no cap is set
    # (empty bands + no default), fall back to per_job behaviour.
    vehicle = work_order.vehicle
    budget = recon_budget_for(vehicle, dealership=dealership)
    if budget is None:
        return work_order, False

    with transaction.atomic():
        wo = recon_service._load_for_transition(work_order)
        # Guard: approve_work_order refuses zero-finding WOs and we
        # want that refusal surfaced up-front (a queued WO with no
        # findings is a dead end for the manager too).
        if wo.finding_links.count() == 0:
            raise BudgetCheckError(
                f"WorkOrder #{wo.pk} has no linked findings; cannot "
                "check budget or authorize."
            )
        prior_spend = recon_spend_for(
            vehicle, dealership=dealership, exclude_wo=wo
        )
        this_wo_total = _wo_estimate_total(wo)
        new_total = prior_spend + this_wo_total
        if new_total <= budget:
            note_prefix = (
                f"auto-authorized: under store recon budget "
                f"(${new_total} of ${budget}). "
            )
            wo.notes = (note_prefix + (wo.notes or "")).strip()
            wo.save(update_fields=["notes", "updated_at"])
            recon_service.approve_work_order(
                wo, dealership=dealership, approved_by=actor
            )
            wo.refresh_from_db()
            return wo, True
        # SESSION_228.1 — a queued WO gets a symmetric note so a
        # manager reading the card sees WHY it is waiting without
        # having to open the queue. "$X over the $Y cap" mirrors
        # the auto-authorized "$X of $Y" line.
        over = new_total - budget
        queue_prefix = (
            f"needs authorization: ${over} over the ${budget} cap. "
        )
        if not (wo.notes or "").startswith("needs authorization:"):
            wo.notes = (queue_prefix + (wo.notes or "")).strip()
            wo.save(update_fields=["notes", "updated_at"])
        return wo, False


# ---- Rate card CRUD -------------------------------------------------------


class CrossTenantRateCardError(ValueError):
    """Raised when a rate-card call touches a row owned by another
    tenant. Mirrors :class:`services.recon.CrossTenantReconError`."""


def _assert_rate_card_tenant(
    item: ReconRateCard, dealership: Dealership
) -> None:
    if item.dealership_id != dealership.pk:
        raise CrossTenantRateCardError(
            f"ReconRateCard #{item.pk} belongs to dealership "
            f"{item.dealership_id}, not {dealership.pk}."
        )


def create_rate_card_item(
    dealership: Dealership,
    *,
    name: str,
    work_order_category: str,
    flat_price,
    variant: str = "",
    retail_default: bool = False,
    active: bool = True,
) -> ReconRateCard:
    item = ReconRateCard(
        dealership=dealership,
        name=name,
        work_order_category=work_order_category,
        flat_price=Decimal(flat_price),
        variant=variant,
        retail_default=retail_default,
        active=active,
    )
    item.full_clean()
    item.save()
    return item


def update_rate_card_item(
    item: ReconRateCard, *, dealership: Dealership, **updates
) -> ReconRateCard:
    _assert_rate_card_tenant(item, dealership)
    allowed = {
        "name",
        "work_order_category",
        "flat_price",
        "variant",
        "retail_default",
        "active",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(
            f"update_rate_card_item: unknown field(s) {sorted(unknown)}. "
            f"Allowed: {sorted(allowed)}."
        )
    for k, v in updates.items():
        if k == "flat_price" and v is not None:
            v = Decimal(v)
        setattr(item, k, v)
    item.full_clean()
    item.save()
    return item


def deactivate_rate_card_item(
    item: ReconRateCard, *, dealership: Dealership
) -> ReconRateCard:
    """Soft-delete a rate-card item by clearing ``active``. Preserves
    the row so historical findings pointing at it (via the M228
    ``rate_card_item`` FK) still render their source name."""
    _assert_rate_card_tenant(item, dealership)
    item.active = False
    item.save(update_fields=["active", "updated_at"])
    return item


def list_rate_card_items(
    dealership: Dealership, *, active_only: bool = True
):
    qs = ReconRateCard.objects.filter(dealership=dealership)
    if active_only:
        qs = qs.filter(active=True)
    return qs.order_by("name", "variant")


# ---- Budget override + Needs-authorization queue helpers ------------------


def record_budget_override(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    amount,
    reason: str,
    granted_by=None,
) -> VehicleReconBudgetOverride:
    """Append a per-vehicle recon-budget override. Non-blank reason
    required — the whole point of the model is the audit trail."""
    amt = Decimal(amount)
    if amt <= 0:
        raise ValueError(
            "record_budget_override: amount must be positive."
        )
    if not (reason or "").strip():
        raise ValueError(
            "record_budget_override: a nonblank reason is required."
        )
    override = VehicleReconBudgetOverride(
        vehicle=vehicle,
        dealership=dealership,
        amount=amt,
        reason=reason.strip(),
        granted_by=granted_by,
    )
    override.full_clean()
    override.save()
    return override


def needs_authorization_queue(dealership: Dealership):
    """Return a queryset of draft WorkOrders for the tenant that
    have at least one linked finding (so an Authorize click would
    succeed) — i.e. WOs that were queued by budget check rather
    than parked as legacy dead-ends.

    Sorted oldest-first so the manager works through the backlog
    in FIFO order — matches "morning triage" ergonomics.
    """
    # SESSION_229 Part 6b — the queue card renders year/make/model
    # and acquisition_total per row, so pull the vehicle's
    # OneToOne acquisition record along with the vehicle to keep
    # acquisition_total off the N+1 path.
    return (
        WorkOrder.objects.filter(
            dealership=dealership,
            status=WORK_ORDER_STATUS_DRAFT,
        )
        .annotate(finding_count=Sum("finding_links__id"))
        .filter(finding_count__isnull=False)
        .select_related("vehicle", "vehicle__acquisition", "vendor")
        .prefetch_related("finding_links__finding", "parts")
        .order_by("created_at")
    )


def overage_for(work_order: WorkOrder, *, dealership: Dealership) -> Decimal:
    """How much this WO would push the car over its recon budget.
    Zero when the WO fits under the cap; positive when it doesn't;
    ``Decimal('0.00')`` when the store isn't in budget mode."""
    budget = recon_budget_for(work_order.vehicle, dealership=dealership)
    if budget is None:
        return _ZERO
    prior_spend = recon_spend_for(
        work_order.vehicle, dealership=dealership, exclude_wo=work_order
    )
    total_with_wo = prior_spend + _wo_estimate_total(work_order)
    delta = total_with_wo - budget
    return _q(delta) if delta > 0 else _ZERO
