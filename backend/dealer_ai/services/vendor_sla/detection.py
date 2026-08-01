"""Milestone 7 · Increment 4 (SESSION_091) — vendor SLA breach detection.

The tenant-scoped service verb that scans outsourced
:class:`WorkOrder` rows for one dealership, applies two SLA policies
(in-progress past ETA + approved-stale > 7 days), emits
:class:`logging.WARNING` records for each breach, and returns a
report of what was flagged.

**Read-only.** The verb does NOT mutate WorkOrder rows or write any
DB rows other than the :class:`JobRunLog` audit row the wrapping
``@instrumented_task`` decorator produces. Notifications land in the
log stream; today's consumer is the operator via log inspection.

**Two rules (thresholds confirmed at SESSION_091 open):**

- ``BREACH_KIND_IN_PROGRESS_PAST_ETA`` —
  ``status='in_progress' AND estimated_completion_date < today``.
  Grace period 0 days (fires on first day past ETA).
- ``BREACH_KIND_APPROVED_STALE`` —
  ``status='approved' AND approved_at::date < today - 7 days``.

**Scope.** Only ``venue='outsourced'`` WOs are scanned. In-house
delays are excluded per SESSION_091 preamble discussion.

**No new models.** The M4 :class:`WorkOrder` model is the substrate.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.4 +
§7 M7.4.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Optional

from ...models import (
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    WorkOrder,
)


# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------

# Approved-stale threshold. A WO at ``status='approved'`` whose
# ``approved_at.date()`` is more than this many days before
# ``as_of.date()`` breaches the SLA. Confirmed at SESSION_091 open
# per M7.4 preamble. Per-dealer configurability is a deliberate M7.4
# non-goal (§1.4). If operator evidence surfaces need, the future
# extension shape is a `DealerOnboardingProfile.vendor_sla_approved_stale_days`
# override that resolves via ``services.dealer_config``.
APPROVED_STALE_THRESHOLD_DAYS = 7

# In-progress ETA grace. A WO at ``status='in_progress'`` whose
# ``estimated_completion_date`` is this many days or more before
# ``as_of.date()`` breaches the SLA. 0 days = "fire on the first day
# past ETA." Confirmed at SESSION_091 open.
IN_PROGRESS_ETA_GRACE_DAYS = 0


# Breach-kind vocabulary. Exposed as string constants (not just enum
# values inside :class:`SlaBreach`) so tests + downstream consumers
# reference them symbolically rather than hard-coding literal strings.
BREACH_KIND_IN_PROGRESS_PAST_ETA = "in_progress_past_eta"
BREACH_KIND_APPROVED_STALE = "approved_stale"


# ---------------------------------------------------------------------------
# Structured logger + record shape
# ---------------------------------------------------------------------------

_LOGGER = logging.getLogger("dealer_ai.vendor_sla.detection")


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlaBreach:
    """One flagged WorkOrder.

    Frozen because the report is immutable once computed — no
    downstream code should mutate a breach record. The
    :class:`WorkOrder` reference is captured so callers can chain
    additional read-only queries; the primary identity for logging /
    persistence remains the ``work_order_id`` field.
    """

    work_order_id: int
    dealership_id: int
    vehicle_stock: str
    vendor_name: str
    kind: str
    breach_days: int
    # Frozen references — captured for callers that want to chain
    # queries without another DB round-trip. Not stored anywhere; the
    # audit trail lives in the log stream + JobRunLog row.
    work_order: WorkOrder = field(compare=False, repr=False)


@dataclass
class SlaBreachReport:
    """Verb execution summary. Consumed by the Celery task shell as a
    structured audit-log payload and by tests as an assertion surface.
    """

    dealership_slug: str
    as_of: dt.date
    breaches: list[SlaBreach] = field(default_factory=list)

    @property
    def breach_count(self) -> int:
        return len(self.breaches)

    @property
    def in_progress_past_eta_count(self) -> int:
        return sum(
            1
            for b in self.breaches
            if b.kind == BREACH_KIND_IN_PROGRESS_PAST_ETA
        )

    @property
    def approved_stale_count(self) -> int:
        return sum(
            1 for b in self.breaches if b.kind == BREACH_KIND_APPROVED_STALE
        )


# ---------------------------------------------------------------------------
# Public verb
# ---------------------------------------------------------------------------


def detect_sla_breaches(
    dealership: Dealership,
    *,
    as_of: Optional[dt.date] = None,
) -> SlaBreachReport:
    """Scan outsourced WorkOrders for one tenant and report SLA breaches.

    Parameters
    ----------
    dealership : Dealership
        The tenant to scan. Required — the verb is single-tenant; the
        M7.4 Celery orchestrator handles multi-tenant fan-out.
    as_of : dt.date, optional
        Reference date for the SLA checks. Defaults to today (in
        ``settings.TIME_ZONE``). Explicit values enable backfill
        scenarios and deterministic testing.

    Returns
    -------
    SlaBreachReport
        Contains the list of flagged WorkOrders. Empty tenant or a
        tenant with no outsourced WOs → empty ``breaches`` list.

    Notes
    -----
    Read-only. Emits :class:`logging.WARNING` records per breach; no
    other side effects.
    """
    if as_of is None:
        # Deferred import — keep the module-import graph free of
        # ``django.utils.timezone`` until actually needed.
        from django.utils import timezone

        as_of = timezone.now().date()

    report = SlaBreachReport(
        dealership_slug=dealership.slug,
        as_of=as_of,
    )

    # Fetch every outsourced, non-terminal WO for the tenant.
    # ``select_related`` avoids N+1 on the vehicle / vendor lookups the
    # breach records need for logging.
    candidates = (
        WorkOrder.objects.filter(
            dealership=dealership,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            status__in=(
                WORK_ORDER_STATUS_APPROVED,
                WORK_ORDER_STATUS_IN_PROGRESS,
            ),
        )
        .select_related("vehicle", "vendor")
        .order_by("pk")
    )

    for wo in candidates:
        breach = _classify(wo, as_of)
        if breach is None:
            continue
        report.breaches.append(breach)
        _LOGGER.warning(
            "vendor_sla.breach kind=%s work_order_id=%d dealership=%s "
            "vehicle=%s vendor=%s breach_days=%d",
            breach.kind,
            breach.work_order_id,
            dealership.slug,
            breach.vehicle_stock,
            breach.vendor_name,
            breach.breach_days,
        )

    return report


# ---------------------------------------------------------------------------
# Internal classification
# ---------------------------------------------------------------------------


def _classify(wo: WorkOrder, as_of: dt.date) -> Optional[SlaBreach]:
    """Return an :class:`SlaBreach` if ``wo`` violates either rule, else
    ``None``.

    Rule precedence: if a WO would breach both rules simultaneously
    (in_progress + also past-approved-stale threshold), rule 1
    (in_progress past ETA) wins because it's the more actionable
    signal — the WO is currently late, not merely stale. This
    precedence is exercised by the M7.4 test suite.
    """
    if wo.status == WORK_ORDER_STATUS_IN_PROGRESS:
        return _classify_in_progress(wo, as_of)
    if wo.status == WORK_ORDER_STATUS_APPROVED:
        return _classify_approved(wo, as_of)
    return None


def _classify_in_progress(
    wo: WorkOrder, as_of: dt.date
) -> Optional[SlaBreach]:
    """Rule 1 — in_progress past ETA."""
    eta = wo.estimated_completion_date
    if eta is None:
        # No ETA promised → cannot breach. Operators should set an ETA
        # at approval time; a missing ETA is a separate data-quality
        # problem, not an SLA breach.
        return None
    breach_days = (as_of - eta).days
    if breach_days < IN_PROGRESS_ETA_GRACE_DAYS + 1:
        # Not yet past ETA (or within the 0-day grace — the +1 fires
        # on the first day *after* ETA, matching the rule "fires on
        # first day past").
        return None
    return SlaBreach(
        work_order_id=wo.pk,
        dealership_id=wo.dealership_id,
        vehicle_stock=wo.vehicle.stock_number,
        vendor_name=wo.vendor.name if wo.vendor else "(no vendor)",
        kind=BREACH_KIND_IN_PROGRESS_PAST_ETA,
        breach_days=breach_days,
        work_order=wo,
    )


def _classify_approved(
    wo: WorkOrder, as_of: dt.date
) -> Optional[SlaBreach]:
    """Rule 2 — approved-stale > threshold days."""
    approved_at = wo.approved_at
    if approved_at is None:
        # ``status='approved'`` without ``approved_at`` is a data-
        # integrity issue the M4.2 service should have prevented; not
        # an SLA breach.
        return None
    days_since_approval = (as_of - approved_at.date()).days
    if days_since_approval <= APPROVED_STALE_THRESHOLD_DAYS:
        return None
    return SlaBreach(
        work_order_id=wo.pk,
        dealership_id=wo.dealership_id,
        vehicle_stock=wo.vehicle.stock_number,
        vendor_name=wo.vendor.name if wo.vendor else "(no vendor)",
        kind=BREACH_KIND_APPROVED_STALE,
        breach_days=days_since_approval,
        work_order=wo,
    )
