"""Milestone 13 · Increment 2 (SESSION_130) — M2 cost reconciliation Celery tasks.

Two Celery tasks matching the M11.5 / M12.3 / M12.4 detector shape:

1. **``post_vehicle_cost_journals_for_dealership``** — per-tenant.
   Posts every unposted, non-estimate VehicleCost for one dealership
   through the M13.1 GL substrate. Returns a summary
   ``{posted_count, failed_count, posted_ids, failed_ids, as_of}``.
2. **``post_vehicle_cost_journals_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 10:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py``. Ninth Celery-beat family — next slot
after M12.4 broken-PTP detector at 09:00, extending the 02:00-09:00
pattern by one hour (§0.a M13.2 decision 3).

**State-transitioning per M11 §6 lesson 17.** ``posted_at``
denormalization is derived state elapsed by "GL post succeeded" —
the detector auto-writes without operator intent. Same posture as
M11.5 / M12.3 / M12.4. Distinct from the M11.4 read-only surfacer
(operator intent required for M11.4 task completion).
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
