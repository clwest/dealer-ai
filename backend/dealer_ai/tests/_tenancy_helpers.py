"""Shared test tenancy helpers (Milestone 1 · Increment 3).

Every ``TestCase`` in this package inherits the ``slug='default'``
:class:`Dealership` row seeded by data-migration
``0009_backfill_dealership_fks``. The write-path pre_save signal
registered in :func:`services.tenancy.register_default_dealership_autofill`
means most existing tests do **not** need code changes — a new
``ChatSession`` / ``Vehicle`` / etc. created without ``dealership=``
gets the default attached automatically.

Tests that want to reference the default tenant explicitly (assertions
about ``related_name`` reverse-accessors, cross-tenant fixtures, etc.)
should either:

- inherit :class:`TenancyTestMixin`, which populates
  ``self.default_dealership`` in ``setUp`` and resets the module-level
  cache in :func:`services.tenancy`, or
- call :func:`default_dealership` directly for one-off lookups.

Kept tiny on purpose. Extension for request-context tenancy lands in
Increment 4; this helper stays default-tenant-only.
"""

from __future__ import annotations

from ..models import Dealership
from ..services.tenancy import (
    get_default_dealership,
    reset_default_dealership_cache,
)


def default_dealership() -> Dealership:
    """Return the migration-seeded default Dealership row."""
    return get_default_dealership()


class TenancyTestMixin:
    """Populate ``self.default_dealership`` for tests that need to
    reference the default tenant explicitly.

    Also clears the module-level PK cache in
    :func:`services.tenancy` so tests that flush / reset the test DB
    don't inherit a stale cache from a prior run.
    """

    def setUp(self) -> None:  # noqa: D401 — Django hook
        super().setUp()  # type: ignore[misc]
        reset_default_dealership_cache()
        self.default_dealership = default_dealership()


# Milestone 5 · Increment 5 (SESSION_079) — retail-gating fixture helper.
#
# Existing tests that create a Vehicle and expect it to appear in
# customer chat / search / showroom must now also seed a VehicleStage
# row at ``frontline`` (the M5.5 refactor swaps the retail-side
# consumers from ``is_available=True`` to
# ``is_retail_eligible=True`` per §5.e Option D SESSION_075
# refined). Wrap the seeding in one helper so a fixture-update sweep
# has a single call to add.
def bootstrap_frontline(vehicle, dealership=None):
    """Seed a ``VehicleStage`` row at ``frontline`` for ``vehicle``.

    Ergonomic wrapper around
    :func:`services.vehicle_lifecycle.ensure_current_stage` with
    ``initial_stage='frontline'``. Idempotent — calling twice on
    the same vehicle is safe.

    ``dealership`` defaults to the vehicle's own ``dealership`` so
    fixture code can call ``bootstrap_frontline(vehicle)``
    without threading the tenant explicitly. Returns the vehicle
    for method-chaining.
    """
    from ..models import VEHICLE_STAGE_FRONTLINE
    from ..services.vehicle_lifecycle import ensure_current_stage

    ensure_current_stage(
        vehicle,
        dealership=dealership if dealership is not None else vehicle.dealership,
        initial_stage=VEHICLE_STAGE_FRONTLINE,
    )
    return vehicle


def wipe_lifecycle_state(vehicle):
    """Delete any :class:`VehicleStage` + :class:`VehicleStageEvent`
    rows for ``vehicle``.

    Convenience helper for M5.1–M5.4 tests that need to exercise
    lifecycle state explicitly (e.g. testing that
    ``get_current_stage`` returns ``None`` for an unseeded
    vehicle). The M5.5 test-only ``post_save`` signal
    auto-bootstraps every newly saved ``Vehicle`` at
    ``frontline``; tests that need the pre-bootstrap state call
    this helper immediately after creating the vehicle.

    Returns the vehicle for chaining.
    """
    from ..models import VehicleStage, VehicleStageEvent

    VehicleStageEvent.objects.filter(vehicle=vehicle).delete()
    VehicleStage.objects.filter(vehicle=vehicle).delete()
    return vehicle
