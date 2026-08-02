"""Milestone 13 · Increment 2 (SESSION_130) — M2 cost reconciliation Celery tasks.
Extended at Milestone 16 · Increment 1 (SESSION_143) — BHPH payment posting.

Four Celery tasks matching the M11.5 / M12.3 / M12.4 detector shape:

1. **``post_vehicle_cost_journals_for_dealership``** — per-tenant.
   Posts every unposted, non-estimate VehicleCost for one dealership
   through the M13.1 GL substrate. Returns a summary
   ``{posted_count, failed_count, posted_ids, failed_ids, as_of}``.
2. **``post_vehicle_cost_journals_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()``.
3. **``post_bhph_payment_journals_for_dealership``** (M16.1) — per-
   tenant BHPH-payment analogue. Posts every unposted BhphPayment
   through :func:`services.accounting.post_bhph_payment_journal`.
4. **``post_bhph_payment_journals_for_all_tenants``** (M16.1) —
   orchestrator counterpart.

**Beat schedule.** The M13.2 orchestrator is scheduled at 10:00; the
M16.1 orchestrator at 11:00 (next open non-overlapping slot per §5.b
Option A). Both ``settings.TIME_ZONE`` daily via
``CELERY_BEAT_SCHEDULE`` in ``dealer_kit/settings.py``. Tenth Celery-
beat family added at M16.1.

**State-transitioning per M11 §6 lesson 17.** Both ``posted_at``
denormalizations are derived state elapsed by "GL post succeeded" —
the detectors auto-write without operator intent. Same posture as
M11.5 / M12.3 / M12.4.
"""

from __future__ import annotations

import logging
from typing import Any

from ..jobs import instrumented_task


_LOGGER = logging.getLogger("dealer_ai.accounting.tasks")


POST_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.accounting.tasks."
    "post_vehicle_cost_journals_for_dealership"
)
POST_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.accounting.tasks."
    "post_vehicle_cost_journals_for_all_tenants"
)

# M16.1 (SESSION_143) — BHPH payment posting task names.
POST_BHPH_PAYMENT_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.accounting.tasks."
    "post_bhph_payment_journals_for_dealership"
)
POST_BHPH_PAYMENT_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.accounting.tasks."
    "post_bhph_payment_journals_for_all_tenants"
)


@instrumented_task(name=POST_FOR_TENANT_TASK_NAME)
def post_vehicle_cost_journals_for_dealership(
    *, dealership_id: int
) -> dict[str, Any]:
    """Post every unposted VehicleCost for one dealership."""
    from ...models import Dealership
    from .vehicle_cost import post_all_unposted_costs_for_dealership

    dealership = Dealership.objects.get(pk=dealership_id)
    return post_all_unposted_costs_for_dealership(dealership=dealership)


@instrumented_task(name=POST_FOR_ALL_TENANTS_TASK_NAME)
def post_vehicle_cost_journals_for_all_tenants() -> dict[str, Any]:
    """Enqueue per-tenant VehicleCost posting for every :class:`Dealership`."""
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        post_vehicle_cost_journals_for_dealership.delay(dealership_id=pk)

    _LOGGER.info(
        "accounting.vehicle_cost.orchestrator dispatched tenants=%d",
        len(dealership_ids),
    )
    return {"dispatched_tenant_count": len(dealership_ids)}


# ---------------------------------------------------------------------------
# Milestone 16 · Increment 1 (SESSION_143) — BHPH payment posting tasks.
# ---------------------------------------------------------------------------


@instrumented_task(name=POST_BHPH_PAYMENT_FOR_TENANT_TASK_NAME)
def post_bhph_payment_journals_for_dealership(
    *, dealership_id: int
) -> dict[str, Any]:
    """Post every unposted BhphPayment for one dealership."""
    from ...models import Dealership
    from .bhph_payment import post_all_unposted_bhph_payments_for_dealership

    dealership = Dealership.objects.get(pk=dealership_id)
    return post_all_unposted_bhph_payments_for_dealership(dealership=dealership)


@instrumented_task(name=POST_BHPH_PAYMENT_FOR_ALL_TENANTS_TASK_NAME)
def post_bhph_payment_journals_for_all_tenants() -> dict[str, Any]:
    """Enqueue per-tenant BhphPayment posting for every :class:`Dealership`."""
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        post_bhph_payment_journals_for_dealership.delay(dealership_id=pk)

    _LOGGER.info(
        "accounting.bhph_payment.orchestrator dispatched tenants=%d",
        len(dealership_ids),
    )
    return {"dispatched_tenant_count": len(dealership_ids)}
