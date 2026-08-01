"""Milestone 4 · Increment 1 — recon admin registration smokes.

Locks the six new admin surfaces registered per
``MILESTONE_4_PLANNING.md`` §2 row 10:

- Vendor
- ReconDecision
- WorkOrder
- WorkOrderFinding
- WorkOrderPart
- VendorCommunication

Also locks the Vendor admin's PROTECT-aligned behavior: hard-delete
is disabled at the admin surface so it does not offer a button that
would fail confusingly at the DB layer. Normal removal is via
``is_active=False``.
"""

from __future__ import annotations

from django.contrib import admin as django_admin
from django.http import HttpRequest
from django.test import RequestFactory, TestCase

from dealer_ai.models import (
    ReconDecision,
    Vendor,
    VendorCommunication,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)


class M41AdminRegistrations(TestCase):
    """All six models are registered with the Django admin site."""

    def test_vendor_registered(self):
        self.assertIn(Vendor, django_admin.site._registry)

    def test_recon_decision_registered(self):
        self.assertIn(ReconDecision, django_admin.site._registry)

    def test_work_order_registered(self):
        self.assertIn(WorkOrder, django_admin.site._registry)

    def test_work_order_finding_registered(self):
        self.assertIn(WorkOrderFinding, django_admin.site._registry)

    def test_work_order_part_registered(self):
        self.assertIn(WorkOrderPart, django_admin.site._registry)

    def test_vendor_communication_registered(self):
        self.assertIn(VendorCommunication, django_admin.site._registry)


class VendorAdminHardDeleteDisabled(TestCase):
    """The PROTECT contract on ``WorkOrder.vendor`` /
    ``VendorCommunication.vendor`` would surface a confusing DB-level
    ``ProtectedError`` if the admin offered a delete button on a
    referenced vendor. The Vendor admin drops
    ``has_delete_permission`` so the affordance is never shown. This
    test locks that behavior."""

    def test_has_delete_permission_returns_false(self):
        rf = RequestFactory()
        request: HttpRequest = rf.get("/admin/dealer_ai/vendor/")
        admin_instance = django_admin.site._registry[Vendor]
        # Both the list and the object-level variant should return False.
        self.assertFalse(admin_instance.has_delete_permission(request))
        vendor = Vendor(name="Test", slug="test-hdp")
        self.assertFalse(admin_instance.has_delete_permission(request, vendor))
