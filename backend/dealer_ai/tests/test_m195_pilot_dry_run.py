"""Milestone 19 · Increment 5 (SESSION_158) — pilot onboarding end-to-end dry-run.

Authoritative end-to-end contract for the pilot-onboarding
substrate. Ships as a regular Django TestCase per §0.a M19.5
decision 1 so every ``manage.py test dealer_ai`` invocation
proves the M19.1-M19.4 substrate holds together.

Structure:

- :class:`FullPilotJourneyDryRun` — one coherent narrative test
  method walking prospect intake → pilot creation → configuration
  → inventory import → user assignment → readiness gate →
  outbound suppression → termination.
- :class:`EndpointE2EDryRunTests` — exercises each of the five
  M19.3+M19.4 admin endpoints in sequence via APIClient against
  a pilot created through the endpoint layer.
- :class:`SafetyGuardDryRunTests` — non-pilot / non-demo safety
  guards (belt-and-suspenders) + cross-tenant isolation.
- :class:`M195ZeroDriftTests` — carriers / permission classes /
  endpoint count assertions extend the growth-only lesson.

Explicitly does NOT ship new business logic. Every verb / endpoint
tested here already lives in M19.1-M19.4.
"""

from __future__ import annotations

import warnings
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
    PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
    PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
    PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
    PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
    PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
    PILOT_PROSPECT_STATE_CONVERTED,
    PILOT_PROSPECT_STATE_QUALIFIED,
    PILOT_TERMINATION_MODE_ARCHIVE,
    ROLE_ADVISOR,
    Dealership,
    PilotOnboardingChecklist,
    PilotOnboardingStep,
    Salesperson,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.demo_store import (
    SuppressedOutbound,
    is_outbound_enabled,
    suppress_if_outbound_disabled,
)
from dealer_ai.services.inventory_import import CSV_FIELDS
from dealer_ai.services.pilot_onboarding import (
    NonPilotImportError,
    NonPilotTerminationError,
    PILOT_IMPORT_SOURCE,
    advance_prospect_state,
    advance_step,
    create_pilot_dealership,
    create_prospect,
    import_pilot_inventory,
    is_pilot_ready,
    list_pilot_dealerships,
    list_prospects,
    terminate_pilot,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES

from ._auth_helpers import (
    authenticated_client,
    make_demo_dealership,
    make_dealership,
    make_pilot_dealership,
    make_user,
)


_HEADER = ",".join(CSV_FIELDS)


def _csv_row(**overrides) -> str:
    values = {name: overrides.get(name, "") for name in CSV_FIELDS}
    return ",".join(str(values[name]) for name in CSV_FIELDS)


def _csv_body(*rows: str) -> bytes:
    return (_HEADER + "\n" + "\n".join(rows)).encode("utf-8")


# ---------------------------------------------------------------------------
# Full pilot journey — one coherent narrative test
# ---------------------------------------------------------------------------


class FullPilotJourneyDryRun(TestCase):
    """End-to-end dry-run walking a prospect from intake through
    terminated pilot. Sub-assertions labeled by phase.

    The narrative:

    1. A demo tester says "I want to try this with my store."
    2. Chris creates a :class:`PilotProspect` referencing the demo
       Dealership the tester used.
    3. Chris qualifies the prospect (prospect → qualified).
    4. Chris creates the pilot Dealership +
       :class:`PilotOnboardingChecklist` (dealership_created fires
       automatically).
    5. Chris advances the prospect qualified → converted, pinning
       the ``converted_dealership`` FK.
    6. Chris configures the store shape by advancing
       ``profile_configured``.
    7. Chris imports the founding-dealer inventory CSV; partial-
       success surfaces one bad row while accepting two good rows.
    8. Chris advances ``inventory_imported``, ``owner_user_added``,
       ``staff_users_added``, and ``capabilities_enabled``.
    9. Chris confirms readiness — ``readiness_confirmed`` advances
       and ``is_ready`` flips to True.
    10. Outbound guard still suppresses (policy field
        ``outbound_enabled=False``).
    11. Cross-tenant isolation holds — a second dealership's data
        does not leak into the pilot's queries.
    12. Belt-and-suspenders guards refuse import + terminate against
        a non-pilot dealership.
    13. Chris terminates the pilot in ``archive`` mode; child rows
        survive, but the pilot leaves the operator surface.
    """

    def test_full_journey(self) -> None:
        # -------------------------------------------------------------------
        # Phase 1 — Demo tester expresses interest; Chris records prospect.
        # -------------------------------------------------------------------
        source_demo = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="m195-source-demo",
        )
        prospect = create_prospect(
            contact_name="Jamie Testworth",
            contact_email="jamie@example.com",
            dealer_business_name="Testworth Auto",
            dealer_type="independent",
            bhph_enabled=True,
            estimated_inventory_size=45,
            source_demo_dealership=source_demo,
        )
        self.assertEqual(prospect.eligibility_state, "prospect")
        self.assertEqual(prospect.source_demo_dealership_id, source_demo.pk)

        # -------------------------------------------------------------------
        # Phase 2 — Chris qualifies the prospect.
        # -------------------------------------------------------------------
        advance_prospect_state(
            prospect=prospect,
            new_state=PILOT_PROSPECT_STATE_QUALIFIED,
            notes_append="Confirmed 45-unit inventory + operator time.",
        )
        prospect.refresh_from_db()
        self.assertEqual(prospect.eligibility_state, "qualified")

        # -------------------------------------------------------------------
        # Phase 3 — Create the pilot dealership + auto-fire the checklist.
        # -------------------------------------------------------------------
        owner = make_user(username="testworth-owner")
        pilot, checklist = create_pilot_dealership(
            slug="testworth-auto",
            name="Testworth Auto",
            owner_user=owner,
            profile_kwargs={"dealership_name": "Testworth Auto"},
        )
        self.assertTrue(pilot.is_pilot)
        self.assertFalse(pilot.is_demo)
        self.assertFalse(pilot.outbound_enabled)
        self.assertIsNone(pilot.terminated_at)
        self.assertEqual(checklist.dealership_id, pilot.pk)
        self.assertFalse(checklist.is_ready)
        # dealership_created step fired atomically.
        self.assertTrue(
            PilotOnboardingStep.objects.filter(
                checklist=checklist,
                step_slug="dealership_created",
                completed_at__isnull=False,
            ).exists()
        )
        # Owner is a dealer_owner at the pilot.
        self.assertTrue(
            UserDealershipRole.objects.filter(
                user=owner, dealership=pilot, role="dealer_owner"
            ).exists()
        )

        # -------------------------------------------------------------------
        # Phase 4 — Convert the prospect, pinning the pilot dealership FK.
        # -------------------------------------------------------------------
        advance_prospect_state(
            prospect=prospect,
            new_state=PILOT_PROSPECT_STATE_CONVERTED,
            converted_dealership=pilot,
        )
        prospect.refresh_from_db()
        self.assertEqual(prospect.eligibility_state, "converted")
        self.assertEqual(prospect.converted_dealership_id, pilot.pk)

        # -------------------------------------------------------------------
        # Phase 5 — Configure store shape.
        # -------------------------------------------------------------------
        advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
            completed_by=owner,
            notes="Set BHPH + subprime lenders.",
        )
        self.assertTrue(
            PilotOnboardingStep.objects.filter(
                checklist=checklist,
                step_slug=PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
            ).exists()
        )

        # -------------------------------------------------------------------
        # Phase 6 — Import the founding-dealer inventory CSV.
        # Partial-success posture: 2 accepted + 1 rejected.
        # -------------------------------------------------------------------
        csv_bytes = _csv_body(
            _csv_row(
                stock_number="TW-1", year="2019", model="F-150", price="32995",
            ),
            _csv_row(
                stock_number="TW-2", year="2020", model="Civic", price="15750",
            ),
            _csv_row(  # bad — missing year
                stock_number="TW-BAD", model="Fusion", price="9000",
            ),
        )
        result = import_pilot_inventory(
            dealership=pilot,
            csv_source=BytesIO(csv_bytes),
            actor=owner,
        )
        self.assertEqual(result.dealership_id, pilot.pk)
        self.assertEqual(
            result.accepted_row_stock_numbers, ("TW-1", "TW-2")
        )
        self.assertEqual(len(result.rejected_rows), 1)
        self.assertEqual(
            result.rejected_rows[0][0]["stock_number"], "TW-BAD"
        )
        self.assertEqual(
            Vehicle.objects.filter(dealership=pilot).count(), 2
        )
        self.assertTrue(
            Vehicle.objects.filter(
                dealership=pilot, source=PILOT_IMPORT_SOURCE
            ).exists()
        )

        # -------------------------------------------------------------------
        # Phase 7 — Advance the inventory checklist step.
        # -------------------------------------------------------------------
        advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
            completed_by=owner,
            notes="2 of 3 rows accepted; TW-BAD needs a year.",
        )

        # -------------------------------------------------------------------
        # Phase 8 — Add staff + assign roles.
        # -------------------------------------------------------------------
        advisor_user = make_user(username="testworth-advisor")
        Salesperson.objects.create(
            dealership=pilot,
            slug="jane-doe",
            name="Jane Doe",
            user=advisor_user,
        )
        UserDealershipRole.objects.create(
            user=advisor_user, dealership=pilot, role=ROLE_ADVISOR
        )

        advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
            completed_by=owner,
        )
        advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
            completed_by=owner,
        )
        advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
            completed_by=owner,
        )

        # -------------------------------------------------------------------
        # Phase 9 — Readiness gate. Pre-confirm: not ready.
        # -------------------------------------------------------------------
        self.assertFalse(is_pilot_ready(pilot))
        advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
            completed_by=owner,
            notes="Chris signed off after operator walkthrough.",
        )
        checklist.refresh_from_db()
        self.assertTrue(checklist.is_ready)
        self.assertTrue(is_pilot_ready(pilot))

        # -------------------------------------------------------------------
        # Phase 10 — Outbound guard still suppresses (policy field).
        # -------------------------------------------------------------------
        pilot.refresh_from_db()
        self.assertFalse(is_outbound_enabled(pilot))
        guard = suppress_if_outbound_disabled(
            pilot, verb_name="dry_run.some.verb"
        )
        self.assertIsInstance(guard, SuppressedOutbound)

        # A demo dealership also suppresses (M19.1 refactor:
        # outbound_enabled controls the guard, not is_demo/is_pilot).
        demo_guard = suppress_if_outbound_disabled(
            source_demo, verb_name="dry_run.some.verb"
        )
        self.assertIsInstance(demo_guard, SuppressedOutbound)

        # -------------------------------------------------------------------
        # Phase 11 — Cross-tenant isolation.
        # -------------------------------------------------------------------
        other = make_dealership(slug="m195-other")
        Vehicle.objects.create(
            dealership=other,
            stock_number="OTHER-1",
            year=2019,
            model="Silverado",
            price="30000",
        )
        # Pilot's vehicle count stays at 2 — the OTHER-1 row is
        # scoped to a different dealership.
        self.assertEqual(
            Vehicle.objects.filter(dealership=pilot).count(), 2
        )
        # And the pilot's memberships stay scoped: OTHER has no
        # UserDealershipRole rows from this flow.
        self.assertEqual(
            UserDealershipRole.objects.filter(dealership=other).count(),
            0,
        )

        # -------------------------------------------------------------------
        # Phase 12 — Belt-and-suspenders guards refuse non-pilot writes.
        # -------------------------------------------------------------------
        with self.assertRaises(NonPilotImportError):
            import_pilot_inventory(
                dealership=source_demo,
                csv_source=BytesIO(_csv_body()),
            )
        with self.assertRaises(NonPilotTerminationError):
            terminate_pilot(
                dealership=source_demo,
                reason="wrong target",
            )

        # -------------------------------------------------------------------
        # Phase 13 — Terminate in archive mode; children survive; pilot
        # leaves list_pilot_dealerships.
        # -------------------------------------------------------------------
        active_before = list_pilot_dealerships()
        self.assertIn(pilot, active_before)
        terminate_pilot(
            dealership=pilot,
            reason="Pilot completed — Testworth signed as customer.",
            actor=owner,
            mode=PILOT_TERMINATION_MODE_ARCHIVE,
        )
        pilot.refresh_from_db()
        self.assertFalse(pilot.is_pilot)
        self.assertIsNotNone(pilot.terminated_at)
        active_after = list_pilot_dealerships()
        self.assertNotIn(pilot, active_after)
        # Archive mode preserved children — Vehicles survive.
        self.assertEqual(
            Vehicle.objects.filter(dealership=pilot).count(), 2
        )
        # Prospect converted_dealership FK still resolves — archive
        # does not delete the Dealership row.
        prospect.refresh_from_db()
        self.assertEqual(prospect.converted_dealership_id, pilot.pk)

        # And the prospect is still discoverable via list_prospects.
        self.assertIn(prospect, list_prospects())


# ---------------------------------------------------------------------------
# Endpoint E2E — hit each of the five M19.3+M19.4 endpoints in sequence
# ---------------------------------------------------------------------------


PILOT_CREATE = "dealer_ai:admin-pilot-create"
PILOT_LIST = "dealer_ai:admin-pilot-list"
PILOT_CHECKLIST_ADVANCE = "dealer_ai:admin-pilot-checklist-advance"
PILOT_INVENTORY_IMPORT = "dealer_ai:admin-pilot-inventory-import"
PILOT_TERMINATE = "dealer_ai:admin-pilot-terminate"


class EndpointE2EDryRunTests(TestCase):
    """Drive every M19.3+M19.4 admin endpoint through a single
    APIClient session in the sequence Chris follows in the playbook."""

    def test_endpoint_sequence(self) -> None:
        operator = make_user(username="m195-operator")
        client_ = authenticated_client(operator)
        owner = make_user(username="m195-endpoint-owner")

        # 1. POST /admin/pilots/create/
        create_resp = client_.post(
            reverse(PILOT_CREATE),
            {
                "slug": "endpoint-pilot",
                "name": "Endpoint Pilot",
                "owner_username": owner.username,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.content)
        body = create_resp.json()["pilot"]
        slug = body["dealership"]["slug"]
        self.assertTrue(body["dealership"]["is_pilot"])

        # 2. GET /admin/pilots/ — the created pilot appears in the list.
        list_resp = client_.get(reverse(PILOT_LIST))
        self.assertEqual(list_resp.status_code, 200)
        listed_slugs = {
            entry["dealership"]["slug"]
            for entry in list_resp.json()["pilots"]
        }
        self.assertIn(slug, listed_slugs)

        # 3. POST /admin/pilots/<slug>/checklist/advance/ — advance
        # profile_configured.
        advance_resp = client_.post(
            reverse(PILOT_CHECKLIST_ADVANCE, kwargs={"slug": slug}),
            {"step_slug": PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED},
            format="json",
        )
        self.assertEqual(advance_resp.status_code, 200, advance_resp.content)
        completed = {
            step["step_slug"]
            for step in advance_resp.json()["pilot"]["checklist"]["steps"]
            if step["completed_at"] is not None
        }
        self.assertIn(PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED, completed)

        # 4. POST /admin/pilots/<slug>/inventory/import/ — multipart upload.
        uploaded = SimpleUploadedFile(
            "pilot.csv",
            _csv_body(
                _csv_row(
                    stock_number="EP-1", year="2020", model="Civic",
                    price="15000",
                )
            ),
            content_type="text/csv",
        )
        import_resp = client_.post(
            reverse(PILOT_INVENTORY_IMPORT, kwargs={"slug": slug}),
            {"csv": uploaded},
            format="multipart",
        )
        self.assertEqual(import_resp.status_code, 200, import_resp.content)
        import_body = import_resp.json()["result"]
        self.assertEqual(
            import_body["accepted_row_stock_numbers"], ["EP-1"]
        )

        # 5. POST /admin/pilots/<slug>/terminate/ — archive mode.
        term_resp = client_.post(
            reverse(PILOT_TERMINATE, kwargs={"slug": slug}),
            {"reason": "Dry-run terminate", "mode": "archive"},
            format="json",
        )
        self.assertEqual(term_resp.status_code, 200, term_resp.content)
        self.assertFalse(
            term_resp.json()["dealership"]["is_pilot"]
        )
        # And the pilot is no longer in the active list.
        after = client_.get(reverse(PILOT_LIST))
        after_slugs = {
            entry["dealership"]["slug"]
            for entry in after.json()["pilots"]
        }
        self.assertNotIn(slug, after_slugs)


# ---------------------------------------------------------------------------
# Safety guards — non-pilot / non-demo refusal + cross-tenant isolation
# ---------------------------------------------------------------------------


class SafetyGuardDryRunTests(TestCase):
    def test_import_against_live_dealership_raises_non_pilot(self) -> None:
        live = make_dealership(slug="m195-live-1")
        with self.assertRaises(NonPilotImportError):
            import_pilot_inventory(
                dealership=live, csv_source=BytesIO(_csv_body())
            )

    def test_terminate_against_live_dealership_raises_non_pilot(self) -> None:
        live = make_dealership(slug="m195-live-2")
        with self.assertRaises(NonPilotTerminationError):
            terminate_pilot(dealership=live, reason="wrong target")

    def test_terminate_against_demo_raises_non_pilot(self) -> None:
        demo = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="m195-terminate-demo",
        )
        with self.assertRaises(NonPilotTerminationError):
            terminate_pilot(dealership=demo, reason="wrong target")

    def test_suppress_if_demo_deprecated_alias_still_works(self) -> None:
        # M19.1 preserved the deprecated alias. Dry-run confirms it
        # continues to route through the new policy-field predicate.
        from dealer_ai.services.demo_store import suppress_if_demo

        pilot = make_pilot_dealership(slug="m195-legacy-alias")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            marker = suppress_if_demo(pilot, verb_name="dry_run.legacy")
        self.assertIsInstance(marker, SuppressedOutbound)

    def test_pilot_prospect_survives_pilot_archive(self) -> None:
        # SET_NULL FK is only nulled if the Dealership row is deleted;
        # archive termination keeps the row alive so the audit trail
        # remains intact.
        pilot = make_pilot_dealership(slug="m195-prospect-audit")
        prospect = create_prospect(
            contact_name="Ada Lovelace",
            contact_email="ada@example.com",
            dealer_business_name="Lovelace Auto",
        )
        advance_prospect_state(
            prospect=prospect, new_state=PILOT_PROSPECT_STATE_QUALIFIED
        )
        advance_prospect_state(
            prospect=prospect,
            new_state=PILOT_PROSPECT_STATE_CONVERTED,
            converted_dealership=pilot,
        )
        terminate_pilot(
            dealership=pilot,
            reason="test-archive",
            mode=PILOT_TERMINATION_MODE_ARCHIVE,
        )
        prospect.refresh_from_db()
        self.assertEqual(prospect.converted_dealership_id, pilot.pk)


# ---------------------------------------------------------------------------
# Zero-drift growth-only assertions
# ---------------------------------------------------------------------------


class M195ZeroDriftTests(TestCase):
    def test_tenancy_carriers_unchanged(self) -> None:
        # M19.5 is doc + test only.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 52)

    def test_endpoint_count_unchanged(self) -> None:
        # M19.5 adds no endpoints.
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 113)

    def test_no_new_permission_class(self) -> None:
        # Zero-drift streak extends to nineteen consecutive milestones.
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
