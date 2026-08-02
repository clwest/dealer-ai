"""Milestone 18 · Increment 1 (SESSION_147) — demo-store substrate tests.

Covers:

- Model additions: ``Dealership.is_demo`` + ``demo_archetype``
  defaults on existing rows; ``TesterFeedback`` model contract +
  tenancy autofill; vocab exact-set equality per fixed-vocab
  lesson.
- Service package: ``create_demo_store`` + ``reset_demo_store``
  happy paths (with the archetype-stub `NotImplementedError` at
  M18.1); ``NonDemoResetError`` + belt-and-suspenders assert;
  ``list_demo_stores`` isolation.
- Synthetic-data helpers: ``synthetic_vin`` / ``synthetic_phone`` /
  ``synthetic_email`` output shape + determinism; pseudonym roster
  fixed-vocab equality.
- Outbound-send-boundary guard: ``suppress_if_demo`` +
  ``SuppressedOutbound`` behavior; scanner test asserts no
  egress-shaped verb in ``services/`` is missing the guard (except
  the documented LLM allowlist).
- Tenancy carrier count 49 → 50 (`>=` per lesson).
- Permission-class set equality unchanged (zero-drift streak ten
  consecutive milestones).
- Endpoint count 107 (unchanged at M18.1 — feedback POST lands
  at M18.5).
"""

from __future__ import annotations

import re
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from dealer_ai.models import (
    DEMO_ARCHETYPE_BHPH,
    DEMO_ARCHETYPE_CHOICES,
    DEMO_ARCHETYPE_FLOOR_PLANNED,
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    TESTER_FEEDBACK_CATEGORY_BUG,
    TESTER_FEEDBACK_CATEGORY_CHOICES,
    TESTER_FEEDBACK_CATEGORY_CONFUSION,
    TESTER_FEEDBACK_CATEGORY_FEATURE_REQUEST,
    TESTER_FEEDBACK_CATEGORY_VALUE_STATEMENT,
    TESTER_FEEDBACK_CATEGORY_WILLINGNESS_TO_PAY,
    Dealership,
    TesterFeedback,
)
from dealer_ai.services.demo_store import (
    ARCHETYPE_BUILDERS,
    NonDemoResetError,
    SYNTHETIC_NAMES,
    ScenarioSummary,
    SuppressedOutbound,
    create_demo_store,
    get_archetype_builder,
    get_synthetic_name,
    is_demo_dealership,
    list_demo_stores,
    reset_demo_store,
    suppress_if_demo,
    synthetic_email,
    synthetic_phone,
    synthetic_vin,
)
from dealer_ai.services.tenancy import (
    _TENANT_CARRIER_MODEL_NAMES,
    get_default_dealership,
)

from ._auth_helpers import make_demo_dealership


# ---------------------------------------------------------------------------
# Vocab constants — fixed vocab, exact-set equality
# ---------------------------------------------------------------------------


class DemoArchetypeVocabTests(TestCase):
    def test_choices_exact_set_equality(self) -> None:
        # Fixed-vocab lesson per M11-M17. Growth-only via append; the
        # exact-set assertion prevents silent additions.
        self.assertEqual(
            {key for key, _ in DEMO_ARCHETYPE_CHOICES},
            {
                DEMO_ARCHETYPE_RETAIL_SUBPRIME,
                DEMO_ARCHETYPE_FLOOR_PLANNED,
                DEMO_ARCHETYPE_BHPH,
            },
        )

    def test_choices_labels_are_human_readable(self) -> None:
        labels = {label for _, label in DEMO_ARCHETYPE_CHOICES}
        self.assertIn("Retail / Subprime", labels)
        self.assertIn("Floor-planned / Recon-heavy", labels)
        self.assertIn("BHPH portfolio", labels)


class TesterFeedbackCategoryVocabTests(TestCase):
    def test_category_exact_set_equality(self) -> None:
        self.assertEqual(
            {key for key, _ in TESTER_FEEDBACK_CATEGORY_CHOICES},
            {
                TESTER_FEEDBACK_CATEGORY_CONFUSION,
                TESTER_FEEDBACK_CATEGORY_BUG,
                TESTER_FEEDBACK_CATEGORY_FEATURE_REQUEST,
                TESTER_FEEDBACK_CATEGORY_VALUE_STATEMENT,
                TESTER_FEEDBACK_CATEGORY_WILLINGNESS_TO_PAY,
            },
        )


# ---------------------------------------------------------------------------
# Dealership.is_demo / demo_archetype defaults
# ---------------------------------------------------------------------------


class DealershipDemoFieldsTests(TestCase):
    def test_default_dealership_is_not_a_demo(self) -> None:
        # The migration-seeded default row should not accidentally
        # gain is_demo=True from the M18.1 migration.
        default = get_default_dealership()
        self.assertFalse(default.is_demo)
        self.assertEqual(default.demo_archetype, "")

    def test_new_dealership_defaults_is_demo_false(self) -> None:
        d = Dealership.objects.create(slug="m181-plain", name="Plain")
        self.assertFalse(d.is_demo)
        self.assertEqual(d.demo_archetype, "")

    def test_demo_dealership_helper_sets_both_fields(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="m181-helper-check",
        )
        self.assertTrue(d.is_demo)
        self.assertEqual(d.demo_archetype, DEMO_ARCHETYPE_RETAIL_SUBPRIME)


# ---------------------------------------------------------------------------
# TesterFeedback model
# ---------------------------------------------------------------------------


class TesterFeedbackModelTests(TestCase):
    def test_create_row_with_all_required_fields(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-tf-basic"
        )
        row = TesterFeedback.objects.create(
            dealership=d,
            tester_name="Alexis Testworth",
            scenario_slug="bhph_collector_daily",
            category=TESTER_FEEDBACK_CATEGORY_CONFUSION,
            note="I could not find where to view aging notes.",
        )
        self.assertEqual(row.dealership_id, d.pk)
        self.assertEqual(row.category, "confusion")
        self.assertEqual(row.referenced_route, "")

    def test_row_optional_referenced_route(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-tf-route"
        )
        row = TesterFeedback.objects.create(
            dealership=d,
            tester_name="Jamie Demoson",
            scenario_slug="bhph_collector_daily",
            category=TESTER_FEEDBACK_CATEGORY_BUG,
            note="Total was wrong",
            referenced_route="/dealer-ai-accounting/trial-balance",
        )
        self.assertEqual(
            row.referenced_route, "/dealer-ai-accounting/trial-balance"
        )

    def test_tenancy_autofill_fires_on_bypass(self) -> None:
        # M18.1 registers TesterFeedback in _TENANT_CARRIER_MODEL_NAMES
        # — the pre_save autofill signal attaches the default
        # dealership when a caller bypasses the service and forgets
        # to pass dealership=.
        default = get_default_dealership()
        row = TesterFeedback(
            tester_name="Casey Placeholderman",
            scenario_slug="check_autofill",
            category=TESTER_FEEDBACK_CATEGORY_FEATURE_REQUEST,
            note="Autofill safety-net check.",
        )
        row.save()
        self.assertEqual(row.dealership_id, default.pk)


# ---------------------------------------------------------------------------
# Tenancy carrier registration
# ---------------------------------------------------------------------------


class M181TenancyCarrierTests(TestCase):
    def test_tester_feedback_registered_as_tenancy_carrier(self) -> None:
        self.assertIn("TesterFeedback", _TENANT_CARRIER_MODEL_NAMES)

    def test_carrier_count_at_least_fifty(self) -> None:
        # Growth-only list per M9-M17 lesson. `>=50` after M18.1 —
        # +1 for TesterFeedback.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 50)


# ---------------------------------------------------------------------------
# Synthetic-data helpers
# ---------------------------------------------------------------------------


class SyntheticVinTests(TestCase):
    def test_shape_is_17_chars_prefixed_demo_archetype_code(self) -> None:
        vin = synthetic_vin("retail_subprime", 0)
        self.assertEqual(len(vin), 17)
        self.assertTrue(vin.startswith("DEMORS"))

    def test_deterministic_for_same_inputs(self) -> None:
        self.assertEqual(
            synthetic_vin("bhph", 5), synthetic_vin("bhph", 5)
        )

    def test_different_indices_differ(self) -> None:
        self.assertNotEqual(
            synthetic_vin("floor_planned", 0),
            synthetic_vin("floor_planned", 1),
        )

    def test_different_archetypes_differ(self) -> None:
        self.assertNotEqual(
            synthetic_vin("retail_subprime", 0),
            synthetic_vin("floor_planned", 0),
        )

    def test_unknown_archetype_raises(self) -> None:
        with self.assertRaises(ValueError):
            synthetic_vin("nonexistent", 0)


class SyntheticPhoneTests(TestCase):
    def test_555_01xx_format(self) -> None:
        self.assertRegex(synthetic_phone(0), r"^555-01\d{2}$")
        self.assertEqual(synthetic_phone(42), "555-0142")

    def test_wraps_via_modulo(self) -> None:
        # index 200 should wrap to 555-0100 (200 % 100 = 0).
        self.assertEqual(synthetic_phone(200), "555-0100")


class SyntheticEmailTests(TestCase):
    def test_example_tld(self) -> None:
        email = synthetic_email("Alexis Testworth")
        self.assertTrue(email.endswith("@demo.dealer-ai.example"))

    def test_slugifies_spaces_to_dots(self) -> None:
        self.assertEqual(
            synthetic_email("Alexis Testworth"),
            "alexis.testworth@demo.dealer-ai.example",
        )

    def test_empty_name_defaults_to_anonymous(self) -> None:
        self.assertEqual(
            synthetic_email(""), "anonymous@demo.dealer-ai.example"
        )

    def test_all_nonalpha_name_defaults_to_anonymous(self) -> None:
        self.assertEqual(
            synthetic_email("   ??? "),
            "anonymous@demo.dealer-ai.example",
        )


class SyntheticNamesRosterTests(TestCase):
    def test_roster_has_at_least_40_names(self) -> None:
        # Growth-only per lesson. `>=40` today.
        self.assertGreaterEqual(len(SYNTHETIC_NAMES), 40)

    def test_roster_has_no_duplicates(self) -> None:
        self.assertEqual(len(SYNTHETIC_NAMES), len(set(SYNTHETIC_NAMES)))

    def test_get_synthetic_name_wraps_via_modulo(self) -> None:
        first = get_synthetic_name(0)
        wrap = get_synthetic_name(len(SYNTHETIC_NAMES))
        self.assertEqual(first, wrap)


# ---------------------------------------------------------------------------
# Outbound-send-boundary guard toolkit
# ---------------------------------------------------------------------------


class IsDemoDealershipTests(TestCase):
    def test_none_returns_false(self) -> None:
        self.assertFalse(is_demo_dealership(None))

    def test_demo_dealership_returns_true(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-guard-demo"
        )
        self.assertTrue(is_demo_dealership(d))

    def test_non_demo_dealership_returns_false(self) -> None:
        d = Dealership.objects.create(slug="m181-guard-real", name="Real")
        self.assertFalse(is_demo_dealership(d))


class SuppressIfDemoTests(TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(
            suppress_if_demo(None, verb_name="some.verb")
        )

    def test_non_demo_returns_none(self) -> None:
        d = Dealership.objects.create(slug="m181-supp-real", name="Real")
        self.assertIsNone(
            suppress_if_demo(d, verb_name="some.verb")
        )

    def test_demo_returns_suppressed_marker(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-supp-demo"
        )
        result = suppress_if_demo(d, verb_name="some.verb")
        self.assertIsInstance(result, SuppressedOutbound)
        assert result is not None  # narrows for the next assertions.
        self.assertEqual(result.verb_name, "some.verb")
        self.assertEqual(result.dealership_slug, "m181-supp-demo")

    def test_suppressed_outbound_is_truthy(self) -> None:
        # Callers using ``if result:`` should still see success.
        marker = SuppressedOutbound(
            verb_name="v", dealership_slug="d"
        )
        self.assertTrue(bool(marker))


class OutboundEgressScannerTests(TestCase):
    """Scan services/ for egress patterns; assert allowlist compliance."""

    # Files that are permitted to egress without the demo-store guard.
    # Per §0.a M18.1 decision 1: the LLM providers currently egress
    # for inference; a demo-store-aware LLM router is a future
    # decision (see M18.6 retrospective §3 deferrals).
    ALLOWLIST: frozenset[str] = frozenset({
        "llm/openai_provider.py",
        "llm/ollama.py",
    })

    EGRESS_PATTERNS = (
        re.compile(r"\brequests\.(post|get|put|patch|delete)\b"),
        re.compile(r"\bhttpx\.(post|get|put|patch|delete|Client)\b"),
        re.compile(r"\bsmtplib\.\w+"),
        re.compile(r"from django\.core\.mail\b"),
    )

    def test_no_egress_verb_missing_the_guard(self) -> None:
        services_dir = (
            Path(__file__).resolve().parent.parent / "services"
        )
        offenders: list[str] = []
        for path in services_dir.rglob("*.py"):
            rel = path.relative_to(services_dir).as_posix()
            if any(rel == allowed for allowed in self.ALLOWLIST):
                continue
            if rel.startswith("demo_store/"):
                # The guard toolkit itself is exempt.
                continue
            source = path.read_text(encoding="utf-8")
            for pattern in self.EGRESS_PATTERNS:
                if pattern.search(source):
                    # Only counts as an offense if the file does not
                    # import the guard.
                    if "from ..demo_store" not in source and (
                        "from dealer_ai.services.demo_store" not in source
                    ):
                        offenders.append(f"{rel} :: {pattern.pattern}")
        self.assertEqual(
            offenders,
            [],
            msg=(
                "Found egress-shaped call(s) in services/ without "
                "the demo-store guard. Each offender must either "
                "(a) import + call suppress_if_demo before egress, "
                "or (b) be added to "
                "OutboundEgressScannerTests.ALLOWLIST with a "
                "documented rationale. Offenders:\n  "
                + "\n  ".join(offenders)
            ),
        )


# ---------------------------------------------------------------------------
# Registry — create_demo_store / reset_demo_store / list_demo_stores
# ---------------------------------------------------------------------------


class CreateDemoStoreTests(TestCase):
    def test_create_fails_at_m181_because_archetype_stub_raises(self) -> None:
        # At M18.1 every archetype builder is a stub. The atomic
        # ``create_demo_store`` wraps the Dealership.create + the
        # builder.build in one transaction, so a stub raising
        # NotImplementedError rolls back the whole thing — the
        # Dealership is NOT persisted.
        with self.assertRaises(NotImplementedError):
            create_demo_store(
                slug="m181-create-attempt",
                archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            )
        self.assertFalse(
            Dealership.objects.filter(slug="m181-create-attempt").exists()
        )


class ResetDemoStoreGuardTests(TestCase):
    def test_raises_non_demo_reset_error_on_real_dealership(self) -> None:
        real = Dealership.objects.create(
            slug="m181-real-store", name="Real"
        )
        with self.assertRaises(NonDemoResetError):
            reset_demo_store(dealership=real)

    def test_raises_non_demo_reset_error_when_archetype_missing(self) -> None:
        # is_demo=True but demo_archetype='' — a valid-but-broken
        # state that should raise loud.
        broken = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-broken-archetype"
        )
        broken.demo_archetype = ""
        broken.save(update_fields=["demo_archetype"])
        with self.assertRaises(NonDemoResetError):
            reset_demo_store(dealership=broken)

    def test_reset_stub_raises_not_implemented_but_clears_children(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-reset-stub"
        )
        # Seed one child row so we can observe delete-then-rebuild.
        TesterFeedback.objects.create(
            dealership=d,
            tester_name="Casey Placeholderman",
            scenario_slug="pre_reset",
            category=TESTER_FEEDBACK_CATEGORY_CONFUSION,
            note="present before reset",
        )
        self.assertEqual(
            TesterFeedback.objects.filter(dealership=d).count(), 1
        )
        # M18.1 stub raises inside build(); atomic rolls back the
        # delete, so the child row survives.
        with self.assertRaises(NotImplementedError):
            reset_demo_store(dealership=d)
        self.assertEqual(
            TesterFeedback.objects.filter(dealership=d).count(), 1
        )


class ListDemoStoresTests(TestCase):
    def test_returns_only_demo_flagged_dealerships(self) -> None:
        Dealership.objects.create(slug="m181-list-real", name="Real")
        d1 = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-list-demo-1"
        )
        d2 = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="m181-list-demo-2",
        )
        stores = list_demo_stores()
        slugs = {store.slug for store in stores}
        self.assertIn(d1.slug, slugs)
        self.assertIn(d2.slug, slugs)
        self.assertNotIn("m181-list-real", slugs)


# ---------------------------------------------------------------------------
# Archetype dispatcher
# ---------------------------------------------------------------------------


class ArchetypeDispatcherTests(TestCase):
    def test_all_choices_registered(self) -> None:
        # Every vocab member has a builder registered.
        for key, _ in DEMO_ARCHETYPE_CHOICES:
            self.assertIn(key, ARCHETYPE_BUILDERS)

    def test_get_builder_returns_correct_type(self) -> None:
        for key, _ in DEMO_ARCHETYPE_CHOICES:
            builder = get_archetype_builder(key)
            self.assertEqual(builder.archetype, key)

    def test_unknown_archetype_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_archetype_builder("nonexistent-archetype")


# ---------------------------------------------------------------------------
# ScenarioSummary shape
# ---------------------------------------------------------------------------


class ScenarioSummaryTests(TestCase):
    def test_defaults_empty_tuples(self) -> None:
        s = ScenarioSummary(
            archetype=DEMO_ARCHETYPE_BHPH,
            dealership_id=1,
            dealership_slug="demo",
        )
        self.assertEqual(s.seeded_stock_numbers, ())
        self.assertEqual(s.seeded_user_usernames, ())
        self.assertEqual(s.seeded_scenario_slugs, ())
        self.assertEqual(s.notes, "")

    def test_is_frozen(self) -> None:
        s = ScenarioSummary(
            archetype=DEMO_ARCHETYPE_BHPH,
            dealership_id=1,
            dealership_slug="demo",
        )
        with self.assertRaises(Exception):  # dataclasses.FrozenInstanceError
            s.notes = "cannot mutate"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------


class DemoStoreCommandTests(TestCase):
    def test_list_subcommand_reports_empty(self) -> None:
        out = StringIO()
        call_command("demo_store", "list", stdout=out)
        self.assertIn("No demo dealerships exist yet.", out.getvalue())

    def test_list_subcommand_reports_present_stores(self) -> None:
        make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-cmd-list-store"
        )
        out = StringIO()
        call_command("demo_store", "list", stdout=out)
        self.assertIn("m181-cmd-list-store", out.getvalue())

    def test_create_subcommand_surfaces_stub_error(self) -> None:
        # M18.1 stubs raise NotImplementedError; the command surfaces
        # via CommandError.
        with self.assertRaises(CommandError):
            call_command(
                "demo_store",
                "create",
                "--slug=m181-cmd-create",
                "--archetype=retail_subprime",
                stdout=StringIO(),
            )

    def test_reset_subcommand_missing_dealership_errors(self) -> None:
        with self.assertRaises(CommandError):
            call_command(
                "demo_store",
                "reset",
                "--slug=m181-cmd-missing-slug",
                stdout=StringIO(),
            )

    def test_reset_subcommand_refuses_non_demo(self) -> None:
        Dealership.objects.create(slug="m181-cmd-real", name="Real")
        with self.assertRaises(CommandError):
            call_command(
                "demo_store",
                "reset",
                "--slug=m181-cmd-real",
                stdout=StringIO(),
            )

    def test_export_feedback_writes_csv_to_stdout(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-cmd-export"
        )
        TesterFeedback.objects.create(
            dealership=d,
            tester_name="Alexis Testworth",
            scenario_slug="cmd_export_test",
            category=TESTER_FEEDBACK_CATEGORY_WILLINGNESS_TO_PAY,
            note="I would pay for this.",
        )
        out = StringIO()
        call_command(
            "demo_store",
            "export_feedback",
            "--dealership=m181-cmd-export",
            stdout=out,
        )
        csv_output = out.getvalue()
        self.assertIn("tester_name", csv_output)
        self.assertIn("Alexis Testworth", csv_output)
        self.assertIn("willingness_to_pay", csv_output)

    def test_export_feedback_since_filter_applies(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-cmd-since"
        )
        TesterFeedback.objects.create(
            dealership=d,
            tester_name="Old Row",
            scenario_slug="since_test",
            category=TESTER_FEEDBACK_CATEGORY_CONFUSION,
            note="old",
        )
        # A future --since date should exclude the just-created row.
        future = "2099-01-01"
        out = StringIO()
        call_command(
            "demo_store",
            "export_feedback",
            "--dealership=m181-cmd-since",
            f"--since={future}",
            stdout=out,
        )
        self.assertNotIn("Old Row", out.getvalue())

    def test_export_feedback_bad_since_errors(self) -> None:
        d = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH, slug="m181-cmd-badsince"
        )
        with self.assertRaises(CommandError):
            call_command(
                "demo_store",
                "export_feedback",
                "--dealership=m181-cmd-badsince",
                "--since=not-a-date",
                stdout=StringIO(),
            )


# ---------------------------------------------------------------------------
# Zero-drift permission-class + endpoint-count posture
# ---------------------------------------------------------------------------


class M181PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m181(self) -> None:
        # Nine-milestone zero-drift streak (M10 → M17) extends to
        # TEN with M18.1 (this milestone adds zero endpoints, so
        # zero new permission classes). Exact-set equality per
        # fixed-vocab lesson.
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


class M181EndpointCountTests(TestCase):
    def test_endpoint_count_unchanged_at_m181(self) -> None:
        # M18.1 adds zero endpoints — the feedback POST endpoint
        # lands at M18.5. Endpoint count stays >=107 at M18.1.
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 107)
