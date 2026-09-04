import sys

from django.apps import AppConfig


class DealerAiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dealer_ai"
    verbose_name = "Dealer AI"

    def ready(self) -> None:
        # Capture the git identity this process booted with, exactly
        # once. Module-level BUILD_IDENTITY in build_identity.py runs at
        # first import. Never call git per-request — a captured value is
        # the whole point of the /health/version/ check.
        from .services import build_identity  # noqa: F401

        # Milestone 1 · Increment 3 — wire the write-path tenancy
        # fallback. Any save() on the six tenant carriers without an
        # explicit dealership= gets the default row attached via the
        # pre_save signal registered here.
        from .services.tenancy import register_default_dealership_autofill

        register_default_dealership_autofill()

        # Import registers the `manage.py check` warnings under
        # dealer_ai.W*.  The 2026-09-03 demo walk showed a dealer
        # boots the stack for a demo — not pytest — so the SDK / model
        # drift needs to surface at startup as a one-line warning.
        from . import checks  # noqa: F401

        # SESSION_241 books-1 — the ``VehicleAcquisition`` post_save
        # receiver in ``services/accounting/acquisition.py`` posts the
        # DR 121000 / CR 100000 (or CR 210000, floored) journal entry
        # the moment a new acquisition row lands. Import registers
        # the receiver via ``@receiver(post_save, sender=...)``;
        # ``register_acquisition_post_save`` exists only to make the
        # wiring explicit alongside the M1.3 tenancy autofill.
        from .services.accounting.acquisition import (
            register_acquisition_post_save,
        )

        register_acquisition_post_save()

        # Milestone 5 · Increment 5 (SESSION_079) — test-only Vehicle
        # stage auto-bootstrap.
        #
        # Registers a post_save signal that seeds a frontline
        # VehicleStage row for every newly saved Vehicle — but ONLY
        # when Django's test runner is active (detected via ``"test"
        # in sys.argv``). Production Vehicle creation paths must
        # remain explicit per MILESTONE_5_PLANNING.md §0.a item 6.
        # See ``dealer_ai/tests/__init__.py`` for the full rationale.
        if _is_running_tests():
            from .tests import _register_test_only_frontline_bootstrap
            _register_test_only_frontline_bootstrap()


def _is_running_tests() -> bool:
    """Return True when Django's test runner is executing.

    Detects via ``sys.argv`` — ``manage.py test`` or
    ``manage.py test <app>``. Also true when the runner is invoked
    programmatically (e.g. ``django-admin test`` or a CI wrapper
    passing ``test`` as the first positional arg).
    """
    if len(sys.argv) < 2:
        return False
    return sys.argv[1] == "test" or "test" in sys.argv
