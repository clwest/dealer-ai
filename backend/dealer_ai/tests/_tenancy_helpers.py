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
