"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive write verb.

Corresponds to SALES §workflow step 6 (demonstration / test drive).
Enforces the M11.2 mandatory-both attach shape (§5.c Option A) —
every test drive must reference a same-tenant CustomerLead and a
same-tenant Vehicle.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from ...models import CustomerLead, Dealership, TestDrive, Vehicle


User = get_user_model()


class CrossTenantTestDriveError(Exception):
    """Raised when a test drive write names a lead or vehicle in another tenant.

    Surfaces at the endpoint layer as 404 (never leak cross-tenant
    existence). Same fail-closed convention as
    :class:`services.f_and_i.CrossTenantCreditApplicationError` and
    :class:`services.leads.CrossTenantReferrerError`.
    """


def record_test_drive(
    *,
    dealership: Dealership,
    lead: CustomerLead,
    vehicle: Vehicle,
    driven_at: Optional[dt.datetime] = None,
    driven_by_user: Optional[Any] = None,
    duration_minutes: Optional[int] = None,
    route_notes: str = "",
    customer_reaction: str = "",
    objections_captured: Optional[list] = None,
    next_action: str = "",
) -> TestDrive:
    """Persist a :class:`TestDrive`.

    Both ``lead`` and ``vehicle`` are mandatory per §5.c Option A;
    both must belong to ``dealership`` or :class:`CrossTenantTestDriveError`
    is raised. ``dealership`` is written explicitly (tenancy
    discipline; the ``services.tenancy`` pre_save autofill is only a
    safety net).

    ``driven_at`` defaults to ``timezone.now()`` when omitted —
    matches operator reality that most drives are recorded at the
    end of the drive, not scheduled ahead.
    """
    if lead.dealership_id != dealership.id:
        raise CrossTenantTestDriveError(
            f"CustomerLead {lead.pk} belongs to another tenant."
        )
    if vehicle.dealership_id != dealership.id:
        raise CrossTenantTestDriveError(
            f"Vehicle {vehicle.pk} belongs to another tenant."
        )

    return TestDrive.objects.create(
        dealership=dealership,
        lead=lead,
        vehicle=vehicle,
        driven_by_user=driven_by_user,
        driven_at=driven_at if driven_at is not None else timezone.now(),
        duration_minutes=duration_minutes,
        route_notes=route_notes or "",
        customer_reaction=customer_reaction or "",
        objections_captured=list(objections_captured) if objections_captured else [],
        next_action=next_action or "",
    )
