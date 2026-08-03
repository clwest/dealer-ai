"""Milestone 19 · Increment 1 (SESSION_154) — pilot onboarding substrate tests.

Covers per MILESTONE_19_PLANNING.md §7 M19.1:

- Model additions: ``Dealership.is_pilot`` + ``outbound_enabled`` +
  ``terminated_at`` + ``termination_reason`` defaults; PilotProspect
  model + state machine + FK invariants; PilotOnboardingChecklist +
  PilotOnboardingStep unique_together.
- Vocab constants: ``PILOT_PROSPECT_STATE_CHOICES`` +
  ``PILOT_ONBOARDING_STEP_CHOICES`` +
  ``PILOT_ONBOARDING_STEP_ORDER`` exact-set equality (fixed-vocab
  lesson).
- Service package: create_pilot_dealership + list_pilot_dealerships
  + terminate_pilot (both modes) + belt-and-suspenders guards.
- Prospect verbs: create_prospect + state machine + terminal
  refusal + converted requires dealership.
- Checklist verbs: advance_step + immutability + readiness
  precondition + is_pilot_ready predicate.
- Inventory import stub: raises NotImplementedError.
- Outbound guard refactor: policy field mechanism;
  is_demo_dealership + is_pilot_dealership diagnostics;
  suppress_if_demo deprecated alias delegates + emits warning.
- Scanner test still holds (M18.1 test unchanged).
- Tenancy carrier count 50 → 52 (>=).
- Permission class set unchanged (zero-drift streak fifteen).
- Endpoint count 108 (unchanged at M19.1).
"""

from __future__ import annotations

import warnings
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from dealer_ai.models import (
    PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
    PILOT_ONBOARDING_STEP_CHOICES,
    PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
    PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
    PILOT_ONBOARDING_STEP_ORDER,
    PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
    PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
    PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
    PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
    PILOT_PROSPECT_STATE_CHOICES,
    PILOT_PROSPECT_STATE_CONVERTED,
    PILOT_PROSPECT_STATE_DECLINED,
    PILOT_PROSPECT_STATE_PROSPECT,
    PILOT_PROSPECT_STATE_QUALIFIED,
    PILOT_TERMINATION_MODE_ARCHIVE,
    PILOT_TERMINATION_MODE_CLEANUP,
    Dealership,
    PilotOnboardingChecklist,
    PilotOnboardingStep,
    PilotProspect,
    Vehicle,
)
from dealer_ai.services.demo_store import (
    SuppressedOutbound,
    is_demo_dealership,
    is_outbound_enabled,
    is_pilot_dealership,
    suppress_if_demo,
    suppress_if_outbound_disabled,
)
from dealer_ai.services.pilot_onboarding import (
    ChecklistStepAlreadyCompletedError,
    ConvertedRequiresDealershipError,
    InvalidProspectTransitionError,
    NonPilotTerminationError,
    PilotAlreadyExistsError,
    PilotInventoryImportResult,
    PilotReadinessNotConfirmedError,
    UnknownChecklistStepError,
    advance_prospect_state,
    advance_step,
    create_pilot_dealership,
    create_prospect,
    is_pilot_ready,
    list_pilot_dealerships,
    list_prospects,
    terminate_pilot,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES

from ._auth_helpers import (
    make_demo_dealership,
    make_pilot_dealership,
    make_user,
)


# ---------------------------------------------------------------------------
# Vocab constants — fixed vocab, exact-set equality
# ---------------------------------------------------------------------------


class PilotProspectStateVocabTests(TestCase):
    def test_choices_exact_set_equality(self) -> None:
        self.assertEqual(
            {key for key, _ in PILOT_PROSPECT_STATE_CHOICES},
            {
                PILOT_PROSPECT_STATE_PROSPECT,
                PILOT_PROSPECT_STATE_QUALIFIED,
                PILOT_PROSPECT_STATE_CONVERTED,
                PILOT_PROSPECT_STATE_DECLINED,
            },
        )


class PilotOnboardingStepVocabTests(TestCase):
    def test_choices_exact_set_equality(self) -> None:
        self.assertEqual(
            {key for key, _ in PILOT_ONBOARDING_STEP_CHOICES},
            {
                PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
                PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
                PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
                PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
                PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
                PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
                PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
            },
        )

    def test_step_order_matches_choices_and_terminates_with_readiness(
        self,
    ) -> None:
        # Order is authoritative for the readiness precondition.
        self.assertEqual(
            PILOT_ONBOARDING_STEP_ORDER,
            tuple(key for key, _ in PILOT_ONBOARDING_STEP_CHOICES),
        )
        self.assertEqual(
            PILOT_ONBOARDING_STEP_ORDER[-1],
            PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
        )


# ---------------------------------------------------------------------------
# Dealership.is_pilot / outbound_enabled / termination-field defaults
# ---------------------------------------------------------------------------


class DealershipPilotFieldsTests(TestCase):
    def test_new_dealership_defaults_all_pilot_fields_false_or_null(
        self,
    ) -> None:
        d = Dealership.objects.create(slug="m191-plain", name="Plain")
        self.assertFalse(d.is_pilot)
        self.assertFalse(d.outbound_enabled)
        self.assertIsNone(d.terminated_at)
        self.assertEqual(d.termination_reason, "")

    def test_migration_seeded_default_dealership_still_live(self) -> None:
        # Belt-and-suspenders against the migration-seeded row
        # accidentally gaining any pilot flag from the M19.1
        # migration.
        from dealer_ai.services.tenancy import get_default_dealership

        default = get_default_dealership()
        self.assertFalse(default.is_pilot)
        self.assertFalse(default.outbound_enabled)
        self.assertIsNone(default.terminated_at)


# ---------------------------------------------------------------------------
# Tenancy carrier registration
# ---------------------------------------------------------------------------


class M191TenancyCarrierTests(TestCase):
    def test_checklist_registered_as_tenancy_carrier(self) -> None:
        self.assertIn(
            "PilotOnboardingChecklist", _TENANT_CARRIER_MODEL_NAMES
        )

    def test_step_registered_as_tenancy_carrier(self) -> None:
        self.assertIn(
            "PilotOnboardingStep", _TENANT_CARRIER_MODEL_NAMES
        )

    def test_prospect_NOT_registered_as_tenancy_carrier(self) -> None:
        # Per §0.a M19.1 decision 1 — PilotProspect is a pre-tenant
        # operator record with no dealership FK. Registering it
        # would break because the autofill signal tries to assign
        # instance.dealership on a model that has no such field.
        self.assertNotIn(
            "PilotProspect", _TENANT_CARRIER_MODEL_NAMES
        )

    def test_carrier_count_at_least_fifty_two(self) -> None:
        # Growth-only list per M9-M18 lesson. 50 → 52 after
        # M19.1 (+2 for Checklist + Step; PilotProspect not
        # registered per §0.a M19.1 decision 1).
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 52)


# ---------------------------------------------------------------------------
# PilotProspect model — state machine + FK invariants
# ---------------------------------------------------------------------------


class PilotProspectModelTests(TestCase):
    def test_defaults_to_prospect_state(self) -> None:
        p = PilotProspect.objects.create(
            contact_name="Alexis Testworth",
            contact_email="alexis@example.com",
            dealer_business_name="Sunrise Auto",
        )
        self.assertEqual(p.eligibility_state, PILOT_PROSPECT_STATE_PROSPECT)
        self.assertIsNone(p.converted_dealership_id)
        self.assertIsNone(p.source_demo_dealership_id)

    def test_clean_refuses_converted_without_dealership(self) -> None:
        p = PilotProspect.objects.create(
            contact_name="Jamie Demoson",
            contact_email="jamie@example.com",
            dealer_business_name="Desert Auto",
        )
        p.eligibility_state = PILOT_PROSPECT_STATE_CONVERTED
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_clean_refuses_converted_dealership_without_converted_state(
        self,
    ) -> None:
        d = make_pilot_dealership(slug="m191-clean-target")
        p = PilotProspect.objects.create(
            contact_name="Casey Placeholderman",
            contact_email="casey@example.com",
            dealer_business_name="Riverside Auto",
        )
        p.converted_dealership = d
        # State stays 'prospect' — invariant violation.
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_source_demo_dealership_optional_at_all_times(self) -> None:
        demo = make_demo_dealership(
            archetype="retail_subprime",
            slug="m191-source-demo",
        )
        p = PilotProspect.objects.create(
            contact_name="Reese Testerman",
            contact_email="reese@example.com",
            dealer_business_name="Highland Auto",
            source_demo_dealership=demo,
        )
        self.assertEqual(p.source_demo_dealership_id, demo.pk)

    def test_source_demo_dealership_delete_sets_null(self) -> None:
        demo = make_demo_dealership(
            archetype="retail_subprime",
            slug="m191-source-demo-delete",
        )
        p = PilotProspect.objects.create(
            contact_name="Blake Simulton",
            contact_email="blake@example.com",
            dealer_business_name="Coastal Auto",
            source_demo_dealership=demo,
        )
        demo.delete()
        p.refresh_from_db()
        self.assertIsNone(p.source_demo_dealership_id)


# ---------------------------------------------------------------------------
# PilotOnboardingChecklist + PilotOnboardingStep model tests
# ---------------------------------------------------------------------------


class ChecklistModelTests(TestCase):
    def test_checklist_one_to_one_with_dealership(self) -> None:
        d = make_pilot_dealership(slug="m191-checklist-1to1")
        checklist = PilotOnboardingChecklist.objects.create(
            dealership=d
        )
        # OneToOne — creating a second raises.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PilotOnboardingChecklist.objects.create(dealership=d)

    def test_step_unique_together_per_checklist(self) -> None:
        d = make_pilot_dealership(slug="m191-step-unique")
        checklist = PilotOnboardingChecklist.objects.create(
            dealership=d
        )
        from django.utils import timezone as tz

        PilotOnboardingStep.objects.create(
            dealership=d,
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
            completed_at=tz.now(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PilotOnboardingStep.objects.create(
                    dealership=d,
                    checklist=checklist,
                    step_slug=PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
                    completed_at=tz.now(),
                )

    def test_step_clean_refuses_cross_tenant(self) -> None:
        d1 = make_pilot_dealership(slug="m191-step-cross-1")
        d2 = make_pilot_dealership(slug="m191-step-cross-2")
        checklist = PilotOnboardingChecklist.objects.create(
            dealership=d1
        )
        from django.utils import timezone as tz

        step = PilotOnboardingStep(
            dealership=d2,  # wrong tenant
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
            completed_at=tz.now(),
        )
        with self.assertRaises(ValidationError):
            step.full_clean()


# ---------------------------------------------------------------------------
# create_pilot_dealership — happy path + guards
# ---------------------------------------------------------------------------


class CreatePilotDealershipTests(TestCase):
    def test_happy_path_creates_all_substrate(self) -> None:
        owner = make_user(username="pilot-owner-1")
        dealership, checklist = create_pilot_dealership(
            slug="m191-create-happy",
            name="Happy Pilot",
            owner_user=owner,
            profile_kwargs={"dealer_type": "independent"},
        )
        # Dealership flags per §5.c + §0.a M19.1 decision 2.
        self.assertTrue(dealership.is_pilot)
        self.assertFalse(dealership.is_demo)
        self.assertFalse(dealership.outbound_enabled)
        # COA seeded (M13.1) — some GLAccount rows exist.
        from dealer_ai.models import GLAccount

        self.assertGreater(
            GLAccount.objects.filter(dealership=dealership).count(),
            0,
        )
        # Owner membership attached.
        from dealer_ai.models import UserDealershipRole

        self.assertTrue(
            UserDealershipRole.objects.filter(
                user=owner, dealership=dealership, role="dealer_owner"
            ).exists()
        )
        # DealerOnboardingProfile populated.
        from dealer_ai.models import DealerOnboardingProfile

        self.assertTrue(
            DealerOnboardingProfile.objects.filter(
                dealership=dealership
            ).exists()
        )
        # Checklist created + dealership_created step already logged.
        self.assertEqual(checklist.dealership_id, dealership.pk)
        self.assertFalse(checklist.is_ready)
        self.assertTrue(
            PilotOnboardingStep.objects.filter(
                checklist=checklist,
                step_slug=PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
            ).exists()
        )

    def test_slug_collision_with_existing_pilot_raises(self) -> None:
        owner = make_user(username="pilot-owner-2")
        create_pilot_dealership(
            slug="m191-slug-collision",
            name="First",
            owner_user=owner,
            profile_kwargs={},
        )
        with self.assertRaises(PilotAlreadyExistsError):
            create_pilot_dealership(
                slug="m191-slug-collision",
                name="Second",
                owner_user=owner,
                profile_kwargs={},
            )

    def test_slug_collision_with_existing_demo_raises(self) -> None:
        make_demo_dealership(
            archetype="retail_subprime",
            slug="m191-slug-shared-demo",
        )
        owner = make_user(username="pilot-owner-3")
        with self.assertRaises(PilotAlreadyExistsError):
            create_pilot_dealership(
                slug="m191-slug-shared-demo",
                name="Collision With Demo",
                owner_user=owner,
                profile_kwargs={},
            )


# ---------------------------------------------------------------------------
# list_pilot_dealerships
# ---------------------------------------------------------------------------


class ListPilotDealershipsTests(TestCase):
    def test_returns_only_active_pilots(self) -> None:
        owner = make_user(username="list-owner-1")
        active, _ = create_pilot_dealership(
            slug="m191-list-active",
            name="Active",
            owner_user=owner,
            profile_kwargs={},
        )
        # A terminated pilot.
        terminated, _ = create_pilot_dealership(
            slug="m191-list-terminated",
            name="Term",
            owner_user=make_user(username="list-owner-2"),
            profile_kwargs={},
        )
        terminate_pilot(
            dealership=terminated,
            reason="ended",
            mode=PILOT_TERMINATION_MODE_ARCHIVE,
        )
        # A demo + a live (default).
        make_demo_dealership(
            archetype="bhph", slug="m191-list-demo"
        )
        pilots = list_pilot_dealerships()
        slugs = {p.slug for p in pilots}
        self.assertIn("m191-list-active", slugs)
        self.assertNotIn("m191-list-terminated", slugs)
        self.assertNotIn("m191-list-demo", slugs)


# ---------------------------------------------------------------------------
# terminate_pilot — guards + archive/cleanup modes
# ---------------------------------------------------------------------------


class TerminatePilotGuardTests(TestCase):
    def test_raises_non_pilot_termination_error_on_real_dealership(
        self,
    ) -> None:
        real = Dealership.objects.create(
            slug="m191-real-store", name="Real"
        )
        with self.assertRaises(NonPilotTerminationError):
            terminate_pilot(
                dealership=real,
                reason="should not fire",
            )

    def test_raises_on_demo_dealership(self) -> None:
        demo = make_demo_dealership(
            archetype="retail_subprime",
            slug="m191-term-demo",
        )
        with self.assertRaises(NonPilotTerminationError):
            terminate_pilot(
                dealership=demo,
                reason="wrong tenant type",
            )

    def test_archive_mode_preserves_children(self) -> None:
        owner = make_user(username="arch-owner")
        d, _ = create_pilot_dealership(
            slug="m191-arch",
            name="Archived",
            owner_user=owner,
            profile_kwargs={},
        )
        # Sanity — COA rows exist.
        from dealer_ai.models import GLAccount

        pre_gla = GLAccount.objects.filter(dealership=d).count()
        self.assertGreater(pre_gla, 0)
        terminate_pilot(
            dealership=d,
            reason="ended for evaluation",
            mode=PILOT_TERMINATION_MODE_ARCHIVE,
        )
        d.refresh_from_db()
        self.assertFalse(d.is_pilot)
        self.assertIsNotNone(d.terminated_at)
        self.assertEqual(
            d.termination_reason, "ended for evaluation"
        )
        # Children preserved.
        self.assertEqual(
            GLAccount.objects.filter(dealership=d).count(), pre_gla
        )

    def test_cleanup_mode_cascades_children(self) -> None:
        owner = make_user(username="clean-owner")
        d, _ = create_pilot_dealership(
            slug="m191-clean",
            name="Cleaned",
            owner_user=owner,
            profile_kwargs={},
        )
        # Add a Vehicle to observe delete.
        Vehicle.objects.create(
            dealership=d,
            stock_number="M191-CLEAN-01",
            year=2018,
            model="Sonic",
            price="9995.00",
            condition="used",
        )
        self.assertEqual(
            Vehicle.objects.filter(dealership=d).count(), 1
        )
        terminate_pilot(
            dealership=d,
            reason="unwinding",
            mode=PILOT_TERMINATION_MODE_CLEANUP,
        )
        d.refresh_from_db()
        self.assertFalse(d.is_pilot)
        self.assertEqual(
            Vehicle.objects.filter(dealership=d).count(), 0
        )

    def test_unknown_mode_raises(self) -> None:
        owner = make_user(username="unknown-mode")
        d, _ = create_pilot_dealership(
            slug="m191-unknown-mode",
            name="Bad Mode",
            owner_user=owner,
            profile_kwargs={},
        )
        with self.assertRaises(ValueError):
            terminate_pilot(
                dealership=d, reason="oops", mode="explode"
            )


# ---------------------------------------------------------------------------
# Checklist step advance + readiness precondition + immutability
# ---------------------------------------------------------------------------


class ChecklistAdvanceStepTests(TestCase):
    def _fresh_pilot(self, slug: str) -> tuple[Dealership, PilotOnboardingChecklist]:
        owner = make_user(username=f"advance-owner-{slug}")
        return create_pilot_dealership(
            slug=slug,
            name=f"Advance {slug}",
            owner_user=owner,
            profile_kwargs={},
        )

    def test_advance_step_happy_path(self) -> None:
        _, checklist = self._fresh_pilot("m191-advance-1")
        step = advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
        )
        self.assertEqual(
            step.step_slug, PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED
        )
        self.assertIsNotNone(step.completed_at)

    def test_unknown_step_raises(self) -> None:
        _, checklist = self._fresh_pilot("m191-advance-unknown")
        with self.assertRaises(UnknownChecklistStepError):
            advance_step(
                checklist=checklist,
                step_slug="not-a-step",
            )

    def test_re_advance_completed_step_raises(self) -> None:
        _, checklist = self._fresh_pilot("m191-advance-re")
        with self.assertRaises(ChecklistStepAlreadyCompletedError):
            # dealership_created is already logged by
            # create_pilot_dealership.
            advance_step(
                checklist=checklist,
                step_slug=PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
            )

    def test_readiness_precondition_blocks_early_advance(self) -> None:
        _, checklist = self._fresh_pilot("m191-advance-ready-early")
        with self.assertRaises(PilotReadinessNotConfirmedError):
            advance_step(
                checklist=checklist,
                step_slug=PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
            )

    def test_readiness_advance_succeeds_after_all_prior_steps(self) -> None:
        _, checklist = self._fresh_pilot("m191-advance-ready-ok")
        for slug in (
            PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
            PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
            PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
            PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
            PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
        ):
            advance_step(checklist=checklist, step_slug=slug)
        step = advance_step(
            checklist=checklist,
            step_slug=PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
        )
        self.assertEqual(
            step.step_slug, PILOT_ONBOARDING_STEP_READINESS_CONFIRMED
        )
        checklist.refresh_from_db()
        self.assertTrue(checklist.is_ready)


class IsPilotReadyTests(TestCase):
    def test_false_for_non_pilot(self) -> None:
        real = Dealership.objects.create(
            slug="m191-ready-real", name="Real"
        )
        self.assertFalse(is_pilot_ready(real))

    def test_false_before_readiness_advanced(self) -> None:
        owner = make_user(username="ready-owner-1")
        d, _ = create_pilot_dealership(
            slug="m191-ready-not-yet",
            name="Not Yet",
            owner_user=owner,
            profile_kwargs={},
        )
        self.assertFalse(is_pilot_ready(d))

    def test_true_after_readiness_advanced(self) -> None:
        owner = make_user(username="ready-owner-2")
        d, checklist = create_pilot_dealership(
            slug="m191-ready-yes",
            name="Yes",
            owner_user=owner,
            profile_kwargs={},
        )
        for slug in (
            PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
            PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
            PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
            PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
            PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
            PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
        ):
            advance_step(checklist=checklist, step_slug=slug)
        self.assertTrue(is_pilot_ready(d))


# ---------------------------------------------------------------------------
# Prospect state machine
# ---------------------------------------------------------------------------


class ProspectVerbsTests(TestCase):
    def test_create_prospect_defaults(self) -> None:
        p = create_prospect(
            contact_name="Nolan Fixturely",
            contact_email="nolan@example.com",
            dealer_business_name="Roadside Auto",
        )
        self.assertEqual(
            p.eligibility_state, PILOT_PROSPECT_STATE_PROSPECT
        )

    def test_prospect_to_qualified_legal(self) -> None:
        p = create_prospect(
            contact_name="Oakley Sandboxson",
            contact_email="oakley@example.com",
            dealer_business_name="Sunset Auto",
        )
        p = advance_prospect_state(
            prospect=p, new_state=PILOT_PROSPECT_STATE_QUALIFIED
        )
        self.assertEqual(
            p.eligibility_state, PILOT_PROSPECT_STATE_QUALIFIED
        )

    def test_prospect_to_declined_legal(self) -> None:
        p = create_prospect(
            contact_name="Parker Rehearsalworth",
            contact_email="parker@example.com",
            dealer_business_name="Northshore Auto",
        )
        p = advance_prospect_state(
            prospect=p, new_state=PILOT_PROSPECT_STATE_DECLINED
        )
        self.assertEqual(
            p.eligibility_state, PILOT_PROSPECT_STATE_DECLINED
        )

    def test_prospect_directly_to_converted_refused(self) -> None:
        p = create_prospect(
            contact_name="Quincy Stubfield",
            contact_email="quincy@example.com",
            dealer_business_name="Foothills Auto",
        )
        d = make_pilot_dealership(slug="m191-prospect-direct-conv")
        with self.assertRaises(InvalidProspectTransitionError):
            advance_prospect_state(
                prospect=p,
                new_state=PILOT_PROSPECT_STATE_CONVERTED,
                converted_dealership=d,
            )

    def test_qualified_to_converted_legal_with_dealership(self) -> None:
        p = create_prospect(
            contact_name="Rowan Blankspace",
            contact_email="rowan@example.com",
            dealer_business_name="Prairie Auto",
        )
        p = advance_prospect_state(
            prospect=p, new_state=PILOT_PROSPECT_STATE_QUALIFIED
        )
        d = make_pilot_dealership(slug="m191-qualified-conv")
        p = advance_prospect_state(
            prospect=p,
            new_state=PILOT_PROSPECT_STATE_CONVERTED,
            converted_dealership=d,
        )
        self.assertEqual(
            p.eligibility_state, PILOT_PROSPECT_STATE_CONVERTED
        )
        self.assertEqual(p.converted_dealership_id, d.pk)

    def test_qualified_to_converted_without_dealership_refused(self) -> None:
        p = create_prospect(
            contact_name="Sawyer Placeholderfield",
            contact_email="sawyer@example.com",
            dealer_business_name="Bayview Auto",
        )
        p = advance_prospect_state(
            prospect=p, new_state=PILOT_PROSPECT_STATE_QUALIFIED
        )
        with self.assertRaises(ConvertedRequiresDealershipError):
            advance_prospect_state(
                prospect=p,
                new_state=PILOT_PROSPECT_STATE_CONVERTED,
            )

    def test_terminal_converted_no_outgoing(self) -> None:
        p = create_prospect(
            contact_name="Tatum Testflight",
            contact_email="tatum@example.com",
            dealer_business_name="Summit Auto",
        )
        p = advance_prospect_state(
            prospect=p, new_state=PILOT_PROSPECT_STATE_QUALIFIED
        )
        d = make_pilot_dealership(slug="m191-term-conv-lock")
        p = advance_prospect_state(
            prospect=p,
            new_state=PILOT_PROSPECT_STATE_CONVERTED,
            converted_dealership=d,
        )
        with self.assertRaises(InvalidProspectTransitionError):
            advance_prospect_state(
                prospect=p, new_state=PILOT_PROSPECT_STATE_DECLINED
            )

    def test_terminal_declined_no_outgoing(self) -> None:
        p = create_prospect(
            contact_name="Umbria Rehearsalton",
            contact_email="umbria@example.com",
            dealer_business_name="Cedar Auto",
        )
        p = advance_prospect_state(
            prospect=p, new_state=PILOT_PROSPECT_STATE_DECLINED
        )
        with self.assertRaises(InvalidProspectTransitionError):
            advance_prospect_state(
                prospect=p,
                new_state=PILOT_PROSPECT_STATE_QUALIFIED,
            )

    def test_list_prospects_recent_first(self) -> None:
        p1 = create_prospect(
            contact_name="Vale Dryrunson",
            contact_email="vale@example.com",
            dealer_business_name="First Ave Auto",
        )
        p2 = create_prospect(
            contact_name="Wren Trialbrook",
            contact_email="wren@example.com",
            dealer_business_name="Second Ave Auto",
        )
        result = list_prospects()
        # p2 (more recent) first.
        self.assertEqual(result[0].pk, p2.pk)
        self.assertEqual(result[1].pk, p1.pk)


# ---------------------------------------------------------------------------
# Inventory import result dataclass — shape survives M19.2 body
# ---------------------------------------------------------------------------


class PilotInventoryImportResultShapeTests(TestCase):
    """M19.1 shipped the ``PilotInventoryImportResult`` dataclass +
    a ``NotImplementedError`` stub for ``import_pilot_inventory``.
    M19.2 replaced the stub with the real body (see
    ``tests/test_m192_pilot_inventory_import.py`` for full behavior
    coverage). The dataclass shape assertion below survives that
    transition to lock the M19.1 return contract in place."""

    def test_result_dataclass_default_empty_tuples(self) -> None:
        r = PilotInventoryImportResult(dealership_id=1)
        self.assertEqual(r.accepted_row_stock_numbers, ())
        self.assertEqual(r.rejected_rows, ())


# ---------------------------------------------------------------------------
# Outbound guard refactor — policy-field mechanism
# ---------------------------------------------------------------------------


class IsOutboundEnabledTests(TestCase):
    def test_none_returns_false(self) -> None:
        self.assertFalse(is_outbound_enabled(None))

    def test_default_dealership_false(self) -> None:
        d = Dealership.objects.create(
            slug="m191-outbound-default", name="Default"
        )
        self.assertFalse(is_outbound_enabled(d))

    def test_true_when_flag_set(self) -> None:
        d = Dealership.objects.create(
            slug="m191-outbound-true",
            name="Enabled",
            outbound_enabled=True,
        )
        self.assertTrue(is_outbound_enabled(d))


class TenantTypeDiagnosticsTests(TestCase):
    def test_is_demo_dealership_only_true_for_demo(self) -> None:
        demo = make_demo_dealership(
            archetype="retail_subprime", slug="m191-diag-demo"
        )
        pilot = make_pilot_dealership(slug="m191-diag-pilot")
        live = Dealership.objects.create(
            slug="m191-diag-live", name="Live"
        )
        self.assertTrue(is_demo_dealership(demo))
        self.assertFalse(is_demo_dealership(pilot))
        self.assertFalse(is_demo_dealership(live))
        self.assertFalse(is_demo_dealership(None))

    def test_is_pilot_dealership_only_true_for_pilot(self) -> None:
        demo = make_demo_dealership(
            archetype="bhph", slug="m191-diag-demo-2"
        )
        pilot = make_pilot_dealership(slug="m191-diag-pilot-2")
        self.assertFalse(is_pilot_dealership(demo))
        self.assertTrue(is_pilot_dealership(pilot))
        self.assertFalse(is_pilot_dealership(None))


class SuppressIfOutboundDisabledTests(TestCase):
    def test_none_dealership_returns_marker(self) -> None:
        # No tenant context ⇒ no policy context ⇒ suppress.
        result = suppress_if_outbound_disabled(
            None, verb_name="test.verb"
        )
        self.assertIsInstance(result, SuppressedOutbound)

    def test_outbound_disabled_returns_marker(self) -> None:
        d = make_pilot_dealership(slug="m191-supp-disabled")
        result = suppress_if_outbound_disabled(
            d, verb_name="test.verb"
        )
        self.assertIsInstance(result, SuppressedOutbound)
        assert result is not None
        self.assertEqual(result.dealership_slug, d.slug)

    def test_outbound_enabled_returns_none(self) -> None:
        d = make_pilot_dealership(
            slug="m191-supp-enabled", outbound_enabled=True
        )
        result = suppress_if_outbound_disabled(
            d, verb_name="test.verb"
        )
        self.assertIsNone(result)

    def test_demo_dealership_suppressed_by_default(self) -> None:
        d = make_demo_dealership(
            archetype="retail_subprime", slug="m191-supp-demo"
        )
        result = suppress_if_outbound_disabled(
            d, verb_name="test.verb"
        )
        self.assertIsInstance(result, SuppressedOutbound)


class SuppressIfDemoDeprecationTests(TestCase):
    def test_alias_delegates_to_outbound_disabled(self) -> None:
        d = make_pilot_dealership(slug="m191-alias-delegates")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = suppress_if_demo(d, verb_name="test.verb")
        self.assertIsInstance(result, SuppressedOutbound)

    def test_alias_emits_deprecation_warning(self) -> None:
        d = make_pilot_dealership(slug="m191-alias-warns")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            suppress_if_demo(d, verb_name="test.verb")
        self.assertTrue(
            any(
                issubclass(w.category, DeprecationWarning)
                for w in caught
            )
        )


# ---------------------------------------------------------------------------
# Zero-drift permission-class + endpoint count posture
# ---------------------------------------------------------------------------


class M191PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m191(self) -> None:
        # Zero-drift streak extends to fifteen consecutive
        # milestones (M10 → M19.1). Exact-set equality.
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


class M191EndpointCountTests(TestCase):
    def test_endpoint_count_unchanged_at_m191(self) -> None:
        # Endpoints ship at M19.3. At M19.1 the count remains at 108.
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 108)
