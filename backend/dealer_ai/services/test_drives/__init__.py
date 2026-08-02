"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive service package.

Wraps the M11.2 :class:`TestDrive` entity write path per
``MILESTONE_11_PLANNING.md`` §1.2 + §5.c Option A. One verb:

- :func:`record_test_drive`

Cross-tenant lead / vehicle references raise
:class:`CrossTenantTestDriveError` (surfaces as 404 at the endpoint
layer, matching the M2.6 / M3.6 / M4.6 / M9.1 / M10.1 / M11.1
fail-closed convention).
"""

from __future__ import annotations

from .test_drive import (
    CrossTenantTestDriveError,
    record_test_drive,
)

__all__ = [
    "CrossTenantTestDriveError",
    "record_test_drive",
]
