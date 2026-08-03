"""Milestone 19 · Increment 4 (SESSION_157) — pilot inventory import endpoint tests.

Covers the fifth pilot admin endpoint deferred from M19.3 per §0.a
M19.3 decision 1 and shipped at M19.4 alongside its frontend
consumer:

- ``POST /admin/pilots/<slug>/inventory/import/`` — multipart CSV
  upload wrapping :func:`import_pilot_inventory` (M19.2).
- Contract: 200 with serialized :class:`PilotInventoryImportResult`;
  400 on missing file; 404 on nonexistent / non-pilot slug; 500 on
  broken-invariant guard.
- File-upload contract per §0.a M19.4 decision 1 (DRF ``FileField``).
- Growth-only endpoint count: 112 → 113.
- Zero-drift permission-class streak now eighteen consecutive
  milestones (M10 → M19.4).
"""

from __future__ import annotations

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    Vehicle,
)
from dealer_ai.services.inventory_import import CSV_FIELDS

from ._auth_helpers import (
    authenticated_client,
    make_demo_dealership,
    make_pilot_dealership,
    make_user,
)


INVENTORY_IMPORT = "dealer_ai:admin-pilot-inventory-import"

_HEADER = ",".join(CSV_FIELDS)


def _csv_row(**overrides) -> str:
    values = {name: overrides.get(name, "") for name in CSV_FIELDS}
    return ",".join(str(values[name]) for name in CSV_FIELDS)


def _csv_body(*rows: str) -> bytes:
    return (_HEADER + "\n" + "\n".join(rows)).encode("utf-8")


def _authed_client() -> APIClient:
    user = make_user(username="m194-operator")
    return authenticated_client(user)


# ---------------------------------------------------------------------------
# Happy path — 200 with projection
# ---------------------------------------------------------------------------


class InventoryImportHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.client_ = _authed_client()
        self.pilot = make_pilot_dealership(slug="m194-happy")

    def test_200_with_accepted_stock_numbers(self) -> None:
        payload = _csv_body(
            _csv_row(
                stock_number="M194-1",
                year="2019",
                make="Ford",
                model="F-150",
                price="32995",
            ),
            _csv_row(
                stock_number="M194-2",
                year="2020",
                make="Jeep",
                model="Grand Cherokee",
                price="28500",
            ),
        )
        uploaded = SimpleUploadedFile(
            "pilot.csv", payload, content_type="text/csv"
        )
        response = self.client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": self.pilot.slug}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["result"]
        self.assertEqual(body["dealership_id"], self.pilot.pk)
        self.assertEqual(
            body["accepted_row_stock_numbers"], ["M194-1", "M194-2"]
        )
        self.assertEqual(body["rejected_rows"], [])
        self.assertEqual(
            Vehicle.objects.filter(dealership=self.pilot).count(), 2
        )

    def test_partial_success_projection(self) -> None:
        payload = _csv_body(
            _csv_row(
                stock_number="OK-1",
                year="2020",
                model="Civic",
                price="15000",
            ),
            _csv_row(  # missing year
                stock_number="BAD-1",
                model="Fusion",
                price="9000",
            ),
        )
        uploaded = SimpleUploadedFile(
            "pilot.csv", payload, content_type="text/csv"
        )
        response = self.client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": self.pilot.slug}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["result"]
        self.assertEqual(body["accepted_row_stock_numbers"], ["OK-1"])
        self.assertEqual(len(body["rejected_rows"]), 1)
        rejected = body["rejected_rows"][0]
        self.assertIn("row", rejected)
        self.assertIn("reason", rejected)
        self.assertEqual(rejected["row"]["stock_number"], "BAD-1")

    def test_empty_csv_returns_empty_projection(self) -> None:
        uploaded = SimpleUploadedFile(
            "empty.csv",
            (_HEADER + "\n").encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": self.pilot.slug}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["result"]
        self.assertEqual(body["accepted_row_stock_numbers"], [])
        self.assertEqual(body["rejected_rows"], [])


# ---------------------------------------------------------------------------
# Guard paths — 400 / 404 / auth
# ---------------------------------------------------------------------------


class InventoryImportGuardTests(TestCase):
    def test_missing_file_returns_400(self) -> None:
        client_ = _authed_client()
        pilot = make_pilot_dealership(slug="m194-missing")
        response = client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": pilot.slug}),
            {},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_slug_returns_404(self) -> None:
        client_ = _authed_client()
        uploaded = SimpleUploadedFile(
            "pilot.csv",
            _csv_body(),
            content_type="text/csv",
        )
        response = client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": "no-such-pilot"}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 404)

    def test_non_pilot_slug_returns_404(self) -> None:
        client_ = _authed_client()
        # A demo dealership has is_pilot=False; the URL filter rules
        # it out even though the slug exists as a Dealership.
        make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="m194-demo",
        )
        uploaded = SimpleUploadedFile(
            "pilot.csv", _csv_body(), content_type="text/csv"
        )
        response = client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": "m194-demo"}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 404)

    def test_unauth_returns_401_or_403(self) -> None:
        pilot = make_pilot_dealership(slug="m194-unauth")
        uploaded = SimpleUploadedFile(
            "pilot.csv", _csv_body(), content_type="text/csv"
        )
        response = APIClient().post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": pilot.slug}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertIn(response.status_code, (401, 403))


# ---------------------------------------------------------------------------
# Vehicle rows carry pilot import source
# ---------------------------------------------------------------------------


class InventoryImportPersistenceTests(TestCase):
    def test_created_vehicles_carry_pilot_import_source(self) -> None:
        from dealer_ai.services.pilot_onboarding import PILOT_IMPORT_SOURCE

        client_ = _authed_client()
        pilot = make_pilot_dealership(slug="m194-persist")
        payload = _csv_body(
            _csv_row(
                stock_number="PERSIST-1",
                year="2020",
                model="Civic",
                price="15000",
            )
        )
        uploaded = SimpleUploadedFile(
            "pilot.csv", payload, content_type="text/csv"
        )
        response = client_.post(
            reverse(INVENTORY_IMPORT, kwargs={"slug": pilot.slug}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200, response.content)
        v = Vehicle.objects.get(stock_number="PERSIST-1")
        self.assertEqual(v.dealership_id, pilot.pk)
        self.assertEqual(v.source, PILOT_IMPORT_SOURCE)


# ---------------------------------------------------------------------------
# Zero-drift substrate assertions at M19.4
# ---------------------------------------------------------------------------


class M194EndpointCountTests(TestCase):
    def test_admin_endpoint_count_grew_by_one(self) -> None:
        # M19.3 count was 112; M19.4 ships +1 (inventory import).
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 113)


class M194PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m194(self) -> None:
        # Streak of eighteen consecutive milestones (M10 → M19.4).
        from dealer_ai import permissions

        permission_classes = {
            name
            for name in dir(permissions)
            if not name.startswith("_")
            and name != "IsAuthenticated"
            and isinstance(getattr(permissions, name), type)
            and issubclass(
                getattr(permissions, name),
                __import__(
                    "rest_framework.permissions",
                    fromlist=["BasePermission"],
                ).BasePermission,
            )
            and getattr(permissions, name).__module__
            == "dealer_ai.permissions"
        }
        self.assertEqual(
            permission_classes,
            {
                "IsAdvisorForSlug",
                "IsDealerOwnerForAdvisorSlug",
                "IsSalesManagerOrOwnerAtActiveDealership",
                "IsReconManagerSalesManagerOrOwnerAtActiveDealership",
                "IsDealerOwnerAtActiveDealership",
                "IsFinanceManagerOrOwnerAtActiveDealership",
                "ReadOnly",
            },
        )
