"""Milestone 7 · Increment 4 (SESSION_091) — vendor SLA warnings.

Owns the scheduled vendor-SLA-breach detection workflow. Reads
`WorkOrder` rows for a tenant, applies two SLA policies, and emits
:class:`logging.WARNING` records for every breach found. The M8
dashboards will aggregate these log records; today's operator surfaces
them via log inspection (roadmap §Milestone 7 Q6 — operator log-
inspection acceptable for v1).

**SLA rules (§1.4, thresholds confirmed at SESSION_091 open):**

1. **In-progress past ETA.** ``status='in_progress' AND
   estimated_completion_date < today`` — the WO is officially past its
   promised completion date. Grace period **0 days** — the warning
   fires on the first day past ETA.
2. **Approved-stale.** ``status='approved' AND
   approved_at < today - 7 days`` — the WO has been sitting approved
   without moving to in_progress for a week. 7 days is the confirmed
   v1 policy; per-dealer configurability deferred until operator
   evidence surfaces.

**Scope narrowed to outsourced.** Only ``venue='outsourced'`` WOs are
scanned. In-house delays are a different operational problem
(dispatch / capacity) and would dilute the signal. In-house tech-delay
detection can land later as a separate job.

**Package layout mirrors M7.2 + M7.3:**

- :mod:`.detection` — the pure service verb
  (:func:`detect_sla_breaches`) + supporting dataclasses and the
  three policy constants.
- :mod:`.tasks` — Celery task shells (per-tenant + all-tenants
  orchestrator). Kept out of the package facade for the same
  import-cycle discipline used by the M7.2 + M7.3 packages.

Public surface (re-exported here):

- :func:`detect_sla_breaches` — the tenant-scoped verb.
- :class:`SlaBreach` — one flagged WorkOrder.
- :class:`SlaBreachReport` — the verb's return value.
- :data:`APPROVED_STALE_THRESHOLD_DAYS` — the 7-day constant, exposed
  so callers / tests reference it symbolically.
- :data:`IN_PROGRESS_ETA_GRACE_DAYS` — the 0-day constant.
"""

from __future__ import annotations

from .detection import (
    APPROVED_STALE_THRESHOLD_DAYS,
    IN_PROGRESS_ETA_GRACE_DAYS,
    SlaBreach,
    SlaBreachReport,
    detect_sla_breaches,
)

__all__ = (
    "APPROVED_STALE_THRESHOLD_DAYS",
    "IN_PROGRESS_ETA_GRACE_DAYS",
    "SlaBreach",
    "SlaBreachReport",
    "detect_sla_breaches",
)
