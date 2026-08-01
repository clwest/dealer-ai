"""Milestone 7 · Increment 3 (SESSION_090) — aging-per-stage snapshots.

Owns the scheduled aging-per-stage snapshot workflow. Reads current
:class:`VehicleStage` rows for a tenant, computes days-in-stage
distributions per lifecycle stage, and writes one
:class:`StageAgingSnapshot` row per stage-with-vehicles. The M8
dashboards will aggregate over these snapshots without re-scanning
:class:`VehicleStage` on every request.

**Chosen at §5.c Option A** (SESSION_088 preamble). Alternative
(compute-on-read at M8 endpoint time) rejected because M8 dashboards
should have predictable latency independent of fleet size.

**Package layout mirrors M7.2 `services/floor_plan/`:**

- :mod:`.snapshots` — the pure service verb
  (:func:`snapshot_stage_ages`) + supporting dataclasses.
- :mod:`.tasks` — Celery task shells (per-tenant worker +
  all-tenants orchestrator). Kept out of this package facade to
  avoid dragging the M7.1 decorator into the import graph when
  callers only need the verb.

Public surface (re-exported here):

- :func:`snapshot_stage_ages` — the tenant-scoped verb.
- :class:`SnapshotResult` — the verb's return value (list of
  written :class:`StageAgingSnapshot` rows + counters).
- :class:`StagePercentiles` — the per-stage math intermediate.
"""

from __future__ import annotations

from .snapshots import (
    SnapshotResult,
    StagePercentiles,
    snapshot_stage_ages,
)

__all__ = (
    "SnapshotResult",
    "StagePercentiles",
    "snapshot_stage_ages",
)
