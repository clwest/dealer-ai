"""Milestone 5 · Increment 5 (SESSION_079) — test-only Vehicle stage
auto-bootstrap signal.

Every Django test module in this package is discovered via this
``__init__.py`` — importing the package first executes this file.
That gives us a single-point-of-registration for a test-only
``post_save`` signal on ``Vehicle`` that auto-seeds a
``VehicleStage`` row at ``frontline`` for every newly saved
Vehicle.

**Why this is here, NOT in production code:**

Per MILESTONE_5_PLANNING.md §0.a item 6 (SESSION_075 refined), the
production write-path integration must be EXPLICIT — every
``Vehicle.objects.create`` call site invokes
``ensure_current_stage(...)`` deliberately, and no ``pre_save`` /
property-read side effect creates lifecycle state. That contract
holds for production code (the sole production write path lives
in ``services/inventory_import.py`` and was updated in the M5.5
refactor to call ``ensure_current_stage`` explicitly).

The test suite is different. Roughly ~150 pre-existing tests
create ``Vehicle`` rows and expect them to appear in customer-
facing surfaces (chat, search). Updating each fixture individually
would be a mechanical sweep with no design value — it would only
move the "auto-seed frontline" call into every test's setUp
method. Registering the signal here achieves the same behavior
via one edit, without polluting production code, and without
requiring a settings flag.

**Why this doesn't undermine §0.a item 6:**

The prohibition targets production write paths — the concern is
that lazy-bootstrapping in production would hide the intent of
"new vehicles start at ``incoming`` and walk the pipeline." That
concern doesn't apply here: tests want their vehicles retail-
visible on creation because the tests are exercising downstream
behavior (chat, search, scrubs) that presupposes the vehicle
exists in retail inventory. Making that setup implicit for tests
is the ergonomic default; making it explicit for production is
the correctness contract.

If a test explicitly needs to test the "vehicle without a stage
row" case (e.g. the M5.2 read-model property tests, the M5.4
``has_stage=False`` dashboard test), that test can just NOT call
``Vehicle.objects.create`` and instead use ``Vehicle(...)`` +
manual state — OR it can delete the auto-created stage row in
its setUp. Both patterns are used by the M5.1–M5.4 test suites.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


_SIGNAL_UID = "dealer_ai.tests.auto_bootstrap_frontline_on_vehicle_save"


def _register_test_only_frontline_bootstrap():
    """Register the ``post_save`` signal exactly once.

    Idempotent via ``dispatch_uid`` — repeated imports of this
    package (e.g. across parallel test workers) don't stack the
    handler.
    """
    from ..models import Vehicle

    @receiver(post_save, sender=Vehicle, dispatch_uid=_SIGNAL_UID)
    def _auto_bootstrap_frontline(sender, instance, created, **kwargs):  # noqa: ARG001
        """Auto-bootstrap a ``frontline`` VehicleStage row on new
        Vehicle saves (test-only). Skips updates and skips vehicles
        that already have a stage row (idempotent — a test that
        explicitly ensures its own stage isn't overridden)."""
        if not created:
            return
        # Local import — avoid module-load cycle.
        from ..models import VehicleStage
        from ..services.vehicle_lifecycle import ensure_current_stage
        from ..models import VEHICLE_STAGE_FRONTLINE

        if instance.dealership_id is None:
            # Race with the pre_save autofill signal — shouldn't
            # happen because pre_save runs first, but guard so the
            # test suite doesn't crash if a Vehicle is manually
            # constructed without a dealership.
            return
        if VehicleStage.objects.filter(vehicle=instance).exists():
            return
        ensure_current_stage(
            instance,
            dealership=instance.dealership,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )


_register_test_only_frontline_bootstrap()
