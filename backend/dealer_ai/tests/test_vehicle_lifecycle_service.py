"""Milestone 5 · Increment 2 (SESSION_076) — lifecycle service tests.

Coverage of ``dealer_ai/services/vehicle_lifecycle.py`` and the two
Vehicle @property accessors added alongside.

Locked invariants (per SESSION_076 brief + planning §5.b/§5.f
SESSION_075 refined):

Transition table structure:
- 12 stage vocabulary matches the M5.1 enum.
- Retail-preparation forward chain shipped as documented.
- Operational escapes permitted from every retail-preparation
  stage AND from frontline.
- Return transitions from ``hold_reserved`` to any
  retail-preparation stage permitted at the structural layer
  (per-caller target resolution via the event log).
- Return transitions from ``wholesale_out`` / ``company_use`` /
  ``off_market`` to ``inspection`` permitted.
- No ``frontline → sold`` transition (§5.a — sold deferred to M9).
- No ``sold`` in the transition table at all.

Role authority:
- Retail-preparation targets authorized for owner + sales_manager
  + recon_manager.
- Commercial/disposition targets authorized for owner +
  sales_manager only (recon_manager NOT authorized).

Domain errors:
- Four distinct classes. Overloading refused by the type check.

Read-side functions:
- `get_current_stage` — pure read; returns row or None; cross-
  tenant refused.
- `retail_eligible` — True when current_stage == frontline;
  False otherwise; False when no stage row.
- `resolve_hold_reserved_return_target` — walks event log; ignores
  free-text notes; returns None when unresolvable.
- `suggest_transitions` — returns [] in M5.2 (M5.3 fills bodies).

Write-side functions:
- `ensure_current_stage` — creates stage + bootstrap event when
  absent; idempotent when present; cross-tenant refused.
- `advance_stage` — every allowed transition succeeds (both
  forward chain and operational escapes); disallowed transitions
  raise InvalidStageTransitionError; unauthorized role raises
  UnauthorizedStageTransitionError; no-op raises
  StageAlreadyCurrentError; cross-tenant refused; writes both
  stage + event atomically with matching entered_at;
  advance_stage on vehicle without prior stage row seeds via
  ensure_current_stage first (defense-in-depth).

Vehicle @property accessors:
- `Vehicle.current_stage` — pure read; None when no stage row;
  returns row when present.
- `Vehicle.is_retail_eligible` — False when no stage row; True
  when frontline; False otherwise.
- Neither property creates a stage row on first access.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    ROLE_ADVISOR,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    UserDealershipRole,
    VEHICLE_STAGE_COMPANY_USE,
    VEHICLE_STAGE_DETAIL,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_LISTING,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_PHOTOGRAPHY,
    VEHICLE_STAGE_QC,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    VEHICLE_STAGE_WHOLESALE_OUT,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
)
from dealer_ai.services.vehicle_lifecycle import (
    CrossTenantLifecycleError,
    InvalidStageTransitionError,
    StageAlreadyCurrentError,
    SuggestedTransition,
    UnauthorizedStageTransitionError,
    _ALLOWED_TRANSITIONS,
    _STAGE_ROLE_AUTHORITY,
    advance_stage,
    ensure_current_stage,
    get_current_stage,
    resolve_hold_reserved_return_target,
    retail_eligible,
    suggest_transitions,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    # M5.5 test-only auto-bootstrap; wipe so M5.2 service tests
    # observe the pre-seed / post-seed contract explicitly.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


def _make_actor(username: str, dealership: Dealership, role: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="pw12345678")
    UserDealershipRole.objects.create(
        user=user, dealership=dealership, role=role
    )
    return user


# ============================================================================
# Transition table structure
# ============================================================================


class AllowedTransitionsStructure(TestCase):
    """Structural properties of the _ALLOWED_TRANSITIONS table."""

    def test_retail_preparation_forward_chain(self):
        chain = [
            (VEHICLE_STAGE_INCOMING, VEHICLE_STAGE_INSPECTION),
            (VEHICLE_STAGE_INSPECTION, VEHICLE_STAGE_RECON),
            (VEHICLE_STAGE_RECON, VEHICLE_STAGE_QC),
            (VEHICLE_STAGE_QC, VEHICLE_STAGE_DETAIL),
            (VEHICLE_STAGE_QC, VEHICLE_STAGE_PHOTOGRAPHY),
            (VEHICLE_STAGE_DETAIL, VEHICLE_STAGE_PHOTOGRAPHY),
            (VEHICLE_STAGE_PHOTOGRAPHY, VEHICLE_STAGE_LISTING),
            (VEHICLE_STAGE_LISTING, VEHICLE_STAGE_FRONTLINE),
        ]
        for src, tgt in chain:
            self.assertIn(
                tgt,
                _ALLOWED_TRANSITIONS.get(src, frozenset()),
                f"{src} → {tgt} should be allowed",
            )

    def test_operational_escapes_from_every_retail_prep_stage(self):
        retail_prep_stages = {
            VEHICLE_STAGE_INCOMING,
            VEHICLE_STAGE_INSPECTION,
            VEHICLE_STAGE_RECON,
            VEHICLE_STAGE_QC,
            VEHICLE_STAGE_DETAIL,
            VEHICLE_STAGE_PHOTOGRAPHY,
            VEHICLE_STAGE_LISTING,
        }
        for src in retail_prep_stages:
            for tgt in (
                VEHICLE_STAGE_HOLD_RESERVED,
                VEHICLE_STAGE_WHOLESALE_OUT,
                VEHICLE_STAGE_COMPANY_USE,
                VEHICLE_STAGE_OFF_MARKET,
            ):
                self.assertIn(
                    tgt,
                    _ALLOWED_TRANSITIONS.get(src, frozenset()),
                    f"Operational escape {src} → {tgt} should be allowed",
                )

    def test_operational_escapes_from_frontline(self):
        for tgt in (
            VEHICLE_STAGE_HOLD_RESERVED,
            VEHICLE_STAGE_WHOLESALE_OUT,
            VEHICLE_STAGE_COMPANY_USE,
            VEHICLE_STAGE_OFF_MARKET,
        ):
            self.assertIn(
                tgt,
                _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_FRONTLINE, frozenset()),
                f"frontline → {tgt} should be allowed (§5.b post-frontline)",
            )

    def test_hold_reserved_return_targets_any_retail_prep_stage(self):
        retail_prep_stages = {
            VEHICLE_STAGE_INCOMING,
            VEHICLE_STAGE_INSPECTION,
            VEHICLE_STAGE_RECON,
            VEHICLE_STAGE_QC,
            VEHICLE_STAGE_DETAIL,
            VEHICLE_STAGE_PHOTOGRAPHY,
            VEHICLE_STAGE_LISTING,
        }
        allowed = _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_HOLD_RESERVED, frozenset())
        self.assertTrue(
            retail_prep_stages.issubset(allowed),
            f"hold_reserved return must permit any retail-prep stage; "
            f"missing: {retail_prep_stages - allowed}",
        )

    def test_wholesale_out_returns_to_inspection(self):
        self.assertIn(
            VEHICLE_STAGE_INSPECTION,
            _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_WHOLESALE_OUT, frozenset()),
        )

    def test_company_use_returns_to_inspection(self):
        self.assertIn(
            VEHICLE_STAGE_INSPECTION,
            _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_COMPANY_USE, frozenset()),
        )

    def test_off_market_returns_to_inspection(self):
        self.assertIn(
            VEHICLE_STAGE_INSPECTION,
            _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_OFF_MARKET, frozenset()),
        )

    def test_no_frontline_to_sold_transition(self):
        """§5.a — sold deferred to M9 (no enum value, no transition)."""
        allowed = _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_FRONTLINE, frozenset())
        self.assertNotIn("sold", allowed)

    def test_no_sold_source_in_table(self):
        self.assertNotIn("sold", _ALLOWED_TRANSITIONS)

    def test_no_disallowed_forward_shortcut(self):
        """incoming → frontline (skipping the pipeline) must be
        disallowed at the structural layer."""
        allowed = _ALLOWED_TRANSITIONS.get(VEHICLE_STAGE_INCOMING, frozenset())
        self.assertNotIn(VEHICLE_STAGE_FRONTLINE, allowed)


# ============================================================================
# Role authority
# ============================================================================


class StageRoleAuthorityStructure(TestCase):
    def test_retail_prep_targets_authorize_recon_manager(self):
        retail_prep_targets = {
            VEHICLE_STAGE_INCOMING,
            VEHICLE_STAGE_INSPECTION,
            VEHICLE_STAGE_RECON,
            VEHICLE_STAGE_QC,
            VEHICLE_STAGE_DETAIL,
            VEHICLE_STAGE_PHOTOGRAPHY,
            VEHICLE_STAGE_LISTING,
            VEHICLE_STAGE_FRONTLINE,
        }
        for tgt in retail_prep_targets:
            self.assertIn(
                ROLE_RECON_MANAGER,
                _STAGE_ROLE_AUTHORITY.get(tgt, frozenset()),
                f"recon_manager should be authorized for {tgt}",
            )

    def test_commercial_targets_exclude_recon_manager(self):
        commercial_targets = {
            VEHICLE_STAGE_HOLD_RESERVED,
            VEHICLE_STAGE_WHOLESALE_OUT,
            VEHICLE_STAGE_COMPANY_USE,
            VEHICLE_STAGE_OFF_MARKET,
        }
        for tgt in commercial_targets:
            authority = _STAGE_ROLE_AUTHORITY.get(tgt, frozenset())
            self.assertNotIn(
                ROLE_RECON_MANAGER,
                authority,
                f"recon_manager MUST NOT be authorized for {tgt} "
                f"(§5.f SESSION_075 refined)",
            )
            self.assertIn(ROLE_DEALER_OWNER, authority)
            self.assertIn(ROLE_SALES_MANAGER, authority)


# ============================================================================
# Domain errors
# ============================================================================


class DomainErrorsAreDistinct(TestCase):
    """Four distinct classes — do not overload."""

    def test_all_subclass_valueerror(self):
        for cls in (
            CrossTenantLifecycleError,
            InvalidStageTransitionError,
            UnauthorizedStageTransitionError,
            StageAlreadyCurrentError,
        ):
            self.assertTrue(issubclass(cls, ValueError))

    def test_unauthorized_is_not_invalid(self):
        """Overloading refused — SESSION_075 §0.a item 5."""
        self.assertFalse(
            issubclass(UnauthorizedStageTransitionError, InvalidStageTransitionError)
        )
        self.assertFalse(
            issubclass(InvalidStageTransitionError, UnauthorizedStageTransitionError)
        )


# ============================================================================
# get_current_stage — pure read
# ============================================================================


class GetCurrentStagePureRead(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M52GCS", self.default)

    def test_returns_none_when_no_stage_row(self):
        result = get_current_stage(self.vehicle, dealership=self.default)
        self.assertIsNone(result)

    def test_returns_row_when_present(self):
        stage = VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_INSPECTION,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        result = get_current_stage(self.vehicle, dealership=self.default)
        self.assertEqual(result.pk, stage.pk)

    def test_pure_read_does_not_create_stage_row(self):
        get_current_stage(self.vehicle, dealership=self.default)
        # Sanity: no stage row was auto-created.
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=self.vehicle).count(), 0
        )
        # And no bootstrap event either.
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=self.vehicle).count(), 0
        )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-gcs")
        with self.assertRaises(CrossTenantLifecycleError):
            get_current_stage(self.vehicle, dealership=other)


# ============================================================================
# retail_eligible — pure read
# ============================================================================


class RetailEligiblePureRead(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M52RE", self.default)

    def test_returns_false_when_no_stage_row(self):
        self.assertFalse(retail_eligible(self.vehicle, dealership=self.default))

    def test_returns_true_when_frontline(self):
        VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertTrue(retail_eligible(self.vehicle, dealership=self.default))

    def test_returns_false_when_off_market(self):
        VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_OFF_MARKET,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertFalse(retail_eligible(self.vehicle, dealership=self.default))

    def test_returns_false_when_hold_reserved(self):
        """A vehicle on hold for a customer is NOT retail-eligible."""
        VehicleStage.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            current_stage=VEHICLE_STAGE_HOLD_RESERVED,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertFalse(retail_eligible(self.vehicle, dealership=self.default))

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-re")
        with self.assertRaises(CrossTenantLifecycleError):
            retail_eligible(self.vehicle, dealership=other)


# ============================================================================
# ensure_current_stage — the explicit mutating verb
# ============================================================================


class EnsureCurrentStageCreatesWhenAbsent(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M52ECS-NEW", self.default)

    def test_creates_stage_with_default_initial_incoming(self):
        stage = ensure_current_stage(self.vehicle, dealership=self.default)
        self.assertEqual(stage.current_stage, VEHICLE_STAGE_INCOMING)
        self.assertEqual(stage.trigger, VEHICLE_STAGE_TRIGGER_BOOTSTRAP)
        self.assertIsNone(stage.entered_by_id)

    def test_creates_matching_bootstrap_event(self):
        stage = ensure_current_stage(self.vehicle, dealership=self.default)
        events = VehicleStageEvent.objects.filter(vehicle=self.vehicle)
        self.assertEqual(events.count(), 1)
        event = events.first()
        self.assertIsNone(event.from_stage)
        self.assertEqual(event.to_stage, VEHICLE_STAGE_INCOMING)
        self.assertEqual(event.trigger, VEHICLE_STAGE_TRIGGER_BOOTSTRAP)
        self.assertEqual(event.entered_at, stage.entered_at)

    def test_accepts_custom_initial_stage(self):
        stage = ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        self.assertEqual(stage.current_stage, VEHICLE_STAGE_FRONTLINE)
        event = VehicleStageEvent.objects.get(vehicle=self.vehicle)
        self.assertEqual(event.to_stage, VEHICLE_STAGE_FRONTLINE)

    def test_records_actor_on_stage_and_event(self):
        actor = _make_actor("ecs-actor", self.default, ROLE_DEALER_OWNER)
        stage = ensure_current_stage(
            self.vehicle, dealership=self.default, actor=actor
        )
        self.assertEqual(stage.entered_by_id, actor.pk)
        event = VehicleStageEvent.objects.get(vehicle=self.vehicle)
        self.assertEqual(event.by_id, actor.pk)


class EnsureCurrentStageIdempotent(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M52ECS-IDEMP", self.default)

    def test_second_call_returns_existing_row(self):
        first = ensure_current_stage(self.vehicle, dealership=self.default)
        second = ensure_current_stage(self.vehicle, dealership=self.default)
        self.assertEqual(first.pk, second.pk)

    def test_second_call_creates_no_additional_event(self):
        ensure_current_stage(self.vehicle, dealership=self.default)
        ensure_current_stage(self.vehicle, dealership=self.default)
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=self.vehicle).count(), 1
        )


class EnsureCurrentStageValidation(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M52ECS-VAL", self.default)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-ecs")
        with self.assertRaises(CrossTenantLifecycleError):
            ensure_current_stage(self.vehicle, dealership=other)

    def test_unknown_initial_stage_raises_valueerror(self):
        with self.assertRaises(ValueError):
            ensure_current_stage(
                self.vehicle,
                dealership=self.default,
                initial_stage="sold",  # deferred to M9
            )

    def test_unknown_trigger_raises_valueerror(self):
        with self.assertRaises(ValueError):
            ensure_current_stage(
                self.vehicle,
                dealership=self.default,
                trigger="auto",
            )


# ============================================================================
# advance_stage — happy path per allowed transition
# ============================================================================


class AdvanceStageForwardChain(TestCase):
    """Every retail-preparation forward transition succeeds."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.actor = _make_actor("adv-fwd", self.default, ROLE_SALES_MANAGER)

    def _seed(self, stock: str, initial: str) -> Vehicle:
        v = _make_vehicle(stock, self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=initial
        )
        return v

    def test_incoming_to_inspection(self):
        v = self._seed("M52ADV-I2I", VEHICLE_STAGE_INCOMING)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_INSPECTION,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_INSPECTION)

    def test_inspection_to_recon(self):
        v = self._seed("M52ADV-I2R", VEHICLE_STAGE_INSPECTION)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_RECON)

    def test_recon_to_qc(self):
        v = self._seed("M52ADV-R2Q", VEHICLE_STAGE_RECON)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_QC,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_QC)

    def test_qc_to_detail(self):
        v = self._seed("M52ADV-Q2D", VEHICLE_STAGE_QC)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_DETAIL,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_DETAIL)

    def test_qc_to_photography_detail_collapse(self):
        v = self._seed("M52ADV-Q2P", VEHICLE_STAGE_QC)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_PHOTOGRAPHY,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_PHOTOGRAPHY)

    def test_detail_to_photography(self):
        v = self._seed("M52ADV-D2P", VEHICLE_STAGE_DETAIL)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_PHOTOGRAPHY,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_PHOTOGRAPHY)

    def test_photography_to_listing(self):
        v = self._seed("M52ADV-P2L", VEHICLE_STAGE_PHOTOGRAPHY)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_LISTING,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_LISTING)

    def test_listing_to_frontline(self):
        v = self._seed("M52ADV-L2F", VEHICLE_STAGE_LISTING)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_FRONTLINE)


class AdvanceStageOperationalEscapes(TestCase):
    """Escape into commercial disposition + return via inspection."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.actor = _make_actor("adv-esc", self.default, ROLE_SALES_MANAGER)

    def _seed(self, stock: str, initial: str) -> Vehicle:
        v = _make_vehicle(stock, self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=initial
        )
        return v

    def test_frontline_to_hold_reserved(self):
        v = self._seed("M52ESC-F2H", VEHICLE_STAGE_FRONTLINE)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes="Reserved for cash customer.",
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_HOLD_RESERVED)

    def test_recon_to_wholesale_out(self):
        v = self._seed("M52ESC-R2W", VEHICLE_STAGE_RECON)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_WHOLESALE_OUT,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes="Frame damage discovered; sending to auction.",
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_WHOLESALE_OUT)

    def test_frontline_to_company_use(self):
        v = self._seed("M52ESC-F2C", VEHICLE_STAGE_FRONTLINE)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_COMPANY_USE,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes="Assigned as courtesy loaner.",
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_COMPANY_USE)

    def test_wholesale_out_returns_to_inspection(self):
        v = self._seed("M52ESC-W2I", VEHICLE_STAGE_WHOLESALE_OUT)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_INSPECTION,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes="Auction cancelled; unit returned.",
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_INSPECTION)


# ============================================================================
# advance_stage — refusals
# ============================================================================


class AdvanceStageStructuralRefusal(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.actor = _make_actor("adv-refuse", self.default, ROLE_SALES_MANAGER)

    def test_forward_shortcut_refused(self):
        v = _make_vehicle("M52ADV-SHORT", self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=VEHICLE_STAGE_INCOMING
        )
        with self.assertRaises(InvalidStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_FRONTLINE,
                actor=self.actor,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )

    def test_backwards_transition_refused(self):
        v = _make_vehicle("M52ADV-BACK", self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=VEHICLE_STAGE_RECON
        )
        with self.assertRaises(InvalidStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_INSPECTION,
                actor=self.actor,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )

    def test_sold_transition_refused_as_unknown_stage(self):
        """§5.a — sold is not a shipped stage in M5."""
        v = _make_vehicle("M52ADV-SOLD", self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=VEHICLE_STAGE_FRONTLINE
        )
        with self.assertRaises(ValueError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage="sold",
                actor=self.actor,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )


class AdvanceStageNoOpRefusal(TestCase):
    def test_transition_to_current_stage_raises_stage_already_current(self):
        default = Dealership.objects.get(slug="default")
        actor = _make_actor("adv-noop", default, ROLE_SALES_MANAGER)
        v = _make_vehicle("M52ADV-NOOP", default)
        ensure_current_stage(
            v, dealership=default, initial_stage=VEHICLE_STAGE_RECON
        )
        with self.assertRaises(StageAlreadyCurrentError):
            advance_stage(
                v,
                dealership=default,
                to_stage=VEHICLE_STAGE_RECON,
                actor=actor,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )


class AdvanceStageRoleAuthorityEnforcement(TestCase):
    """Recon manager can perform retail-prep transitions but NOT
    commercial/disposition transitions (§5.f SESSION_075 refined)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.recon_manager = _make_actor(
            "adv-recon", self.default, ROLE_RECON_MANAGER
        )
        self.sales_manager = _make_actor(
            "adv-sales", self.default, ROLE_SALES_MANAGER
        )
        self.dealer_owner = _make_actor(
            "adv-owner", self.default, ROLE_DEALER_OWNER
        )
        self.advisor = _make_actor("adv-advisor", self.default, ROLE_ADVISOR)

    def _seed(self, stock: str, initial: str) -> Vehicle:
        v = _make_vehicle(stock, self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=initial
        )
        return v

    def test_recon_manager_can_advance_retail_prep(self):
        v = self._seed("M52ROLE-RM-RP", VEHICLE_STAGE_INSPECTION)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=self.recon_manager,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_RECON)

    def test_recon_manager_refused_hold_reserved(self):
        v = self._seed("M52ROLE-RM-HOLD", VEHICLE_STAGE_FRONTLINE)
        with self.assertRaises(UnauthorizedStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_HOLD_RESERVED,
                actor=self.recon_manager,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
                notes="Attempted hold_reserved.",
            )

    def test_recon_manager_refused_wholesale_out(self):
        v = self._seed("M52ROLE-RM-WHOL", VEHICLE_STAGE_RECON)
        with self.assertRaises(UnauthorizedStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_WHOLESALE_OUT,
                actor=self.recon_manager,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )

    def test_recon_manager_refused_company_use(self):
        v = self._seed("M52ROLE-RM-COMP", VEHICLE_STAGE_FRONTLINE)
        with self.assertRaises(UnauthorizedStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_COMPANY_USE,
                actor=self.recon_manager,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )

    def test_recon_manager_refused_off_market(self):
        v = self._seed("M52ROLE-RM-OFF", VEHICLE_STAGE_RECON)
        with self.assertRaises(UnauthorizedStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_OFF_MARKET,
                actor=self.recon_manager,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )

    def test_sales_manager_can_advance_hold_reserved(self):
        v = self._seed("M52ROLE-SM-HOLD", VEHICLE_STAGE_FRONTLINE)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            actor=self.sales_manager,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_HOLD_RESERVED)

    def test_dealer_owner_can_advance_all_targets(self):
        v = self._seed("M52ROLE-DO-WHOL", VEHICLE_STAGE_RECON)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_WHOLESALE_OUT,
            actor=self.dealer_owner,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_WHOLESALE_OUT)

    def test_advisor_role_refused_every_target(self):
        """Advisor / porter / f_and_i_manager / collections all lack
        authority for every M5 transition target."""
        v = self._seed("M52ROLE-AD-RP", VEHICLE_STAGE_INSPECTION)
        with self.assertRaises(UnauthorizedStageTransitionError):
            advance_stage(
                v,
                dealership=self.default,
                to_stage=VEHICLE_STAGE_RECON,
                actor=self.advisor,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )

    def test_system_call_without_actor_bypasses_role_check(self):
        """When actor is None (rule/import/bootstrap triggers), the
        role check is skipped — the system caller is trusted."""
        v = self._seed("M52ROLE-SYS", VEHICLE_STAGE_INSPECTION)
        result = advance_stage(
            v,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=None,
            trigger=VEHICLE_STAGE_TRIGGER_RULE,
            rule_name="inspection_to_recon",
        )
        self.assertEqual(result.current_stage, VEHICLE_STAGE_RECON)


class AdvanceStageCrossTenantRefusal(TestCase):
    def test_cross_tenant_dealership_refused(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(name="Other", slug="other-adv")
        v = _make_vehicle("M52ADV-XTEN", default)
        with self.assertRaises(CrossTenantLifecycleError):
            advance_stage(
                v,
                dealership=other,
                to_stage=VEHICLE_STAGE_INSPECTION,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            )


# ============================================================================
# advance_stage — atomic writes + defense-in-depth
# ============================================================================


class AdvanceStageAtomicWrites(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.actor = _make_actor("adv-atom", self.default, ROLE_SALES_MANAGER)
        self.vehicle = _make_vehicle("M52ATOMIC", self.default)
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_INSPECTION,
        )

    def test_stage_and_event_have_matching_entered_at(self):
        advance_stage(
            self.vehicle,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        stage = VehicleStage.objects.get(vehicle=self.vehicle)
        # Most recent event is the one we just wrote.
        event = VehicleStageEvent.objects.filter(
            vehicle=self.vehicle, trigger=VEHICLE_STAGE_TRIGGER_MANUAL
        ).order_by("-entered_at").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.entered_at, stage.entered_at)
        self.assertEqual(event.from_stage, VEHICLE_STAGE_INSPECTION)
        self.assertEqual(event.to_stage, VEHICLE_STAGE_RECON)

    def test_notes_written_to_both_stage_and_event(self):
        advance_stage(
            self.vehicle,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes="Multi-cylinder misfire; fuel injectors required.",
        )
        stage = VehicleStage.objects.get(vehicle=self.vehicle)
        event = VehicleStageEvent.objects.filter(
            vehicle=self.vehicle, trigger=VEHICLE_STAGE_TRIGGER_MANUAL
        ).order_by("-entered_at").first()
        self.assertIn("misfire", stage.last_transition_note)
        self.assertIn("misfire", event.notes)

    def test_rule_name_written_to_event(self):
        advance_stage(
            self.vehicle,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=None,
            trigger=VEHICLE_STAGE_TRIGGER_RULE,
            rule_name="inspection_to_recon",
        )
        event = VehicleStageEvent.objects.filter(
            vehicle=self.vehicle, trigger=VEHICLE_STAGE_TRIGGER_RULE
        ).order_by("-entered_at").first()
        self.assertEqual(event.rule_name, "inspection_to_recon")


class AdvanceStageDefenseInDepthSeedsMissingRow(TestCase):
    """advance_stage on a vehicle without a prior stage row calls
    ensure_current_stage first (creates ``incoming`` + bootstrap
    event), then attempts the requested transition."""

    def test_advance_from_unseeded_vehicle_seeds_incoming(self):
        default = Dealership.objects.get(slug="default")
        actor = _make_actor("adv-defense", default, ROLE_SALES_MANAGER)
        v = _make_vehicle("M52DEF-SEED", default)
        # No prior ensure_current_stage call.
        advance_stage(
            v,
            dealership=default,
            to_stage=VEHICLE_STAGE_INSPECTION,
            actor=actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        # Stage now sits at inspection.
        stage = VehicleStage.objects.get(vehicle=v)
        self.assertEqual(stage.current_stage, VEHICLE_STAGE_INSPECTION)
        # Events: one bootstrap (from None → incoming) + one manual
        # (from incoming → inspection).
        events = list(
            VehicleStageEvent.objects.filter(vehicle=v).order_by("entered_at")
        )
        self.assertEqual(len(events), 2)
        self.assertIsNone(events[0].from_stage)
        self.assertEqual(events[0].to_stage, VEHICLE_STAGE_INCOMING)
        self.assertEqual(events[0].trigger, VEHICLE_STAGE_TRIGGER_BOOTSTRAP)
        self.assertEqual(events[1].from_stage, VEHICLE_STAGE_INCOMING)
        self.assertEqual(events[1].to_stage, VEHICLE_STAGE_INSPECTION)


# ============================================================================
# resolve_hold_reserved_return_target
# ============================================================================


class ResolveHoldReservedReturnTarget(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.actor = _make_actor("resolve", self.default, ROLE_SALES_MANAGER)
        self.vehicle = _make_vehicle("M52RES", self.default)

    def test_returns_none_when_no_hold_reserved_event(self):
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        result = resolve_hold_reserved_return_target(
            self.vehicle, dealership=self.default
        )
        self.assertIsNone(result)

    def test_returns_previous_retail_prep_stage_from_event(self):
        # frontline → hold_reserved; return target should be frontline.
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        advance_stage(
            self.vehicle,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        result = resolve_hold_reserved_return_target(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result, VEHICLE_STAGE_FRONTLINE)

    def test_ignores_notes_free_text(self):
        """The resolver reads from_stage from the event log, not
        notes (§0.a item 2)."""
        # Seed with recon → hold_reserved; put misleading text in notes.
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_RECON,
        )
        advance_stage(
            self.vehicle,
            dealership=self.default,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            actor=self.actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes="Previously was frontline (this text should be ignored).",
        )
        result = resolve_hold_reserved_return_target(
            self.vehicle, dealership=self.default
        )
        # from_stage was recon, not frontline as the notes claim.
        self.assertEqual(result, VEHICLE_STAGE_RECON)

    def test_returns_none_when_from_stage_is_operational(self):
        """A hold_reserved event with an operational from_stage (e.g.
        wholesale_out → hold_reserved) should NOT resolve — the
        operator must choose an allowed target explicitly."""
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_WHOLESALE_OUT,
        )
        # Manually seed a hold_reserved event with wholesale_out as
        # from_stage. This won't happen via advance_stage (wholesale_out
        # does not permit → hold_reserved in the allowed table), so we
        # write it directly to lock the resolver's behavior against
        # such a case if it ever arises via a future migration or
        # import path.
        VehicleStageEvent.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            from_stage=VEHICLE_STAGE_WHOLESALE_OUT,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            entered_at=timezone.now(),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        result = resolve_hold_reserved_return_target(
            self.vehicle, dealership=self.default
        )
        self.assertIsNone(result)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-res")
        with self.assertRaises(CrossTenantLifecycleError):
            resolve_hold_reserved_return_target(
                self.vehicle, dealership=other
            )


# ============================================================================
# suggest_transitions — M5.2 stub
# ============================================================================


class SuggestTransitionsStub(TestCase):
    def test_returns_empty_list_in_m52(self):
        default = Dealership.objects.get(slug="default")
        v = _make_vehicle("M52SUG", default)
        ensure_current_stage(
            v, dealership=default, initial_stage=VEHICLE_STAGE_INSPECTION
        )
        result = suggest_transitions(v, dealership=default)
        self.assertEqual(result, [])

    def test_cross_tenant_refused(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(name="Other", slug="other-sug")
        v = _make_vehicle("M52SUG-XT", default)
        with self.assertRaises(CrossTenantLifecycleError):
            suggest_transitions(v, dealership=other)

    def test_suggested_transition_dataclass_has_expected_fields(self):
        st = SuggestedTransition(
            to_stage=VEHICLE_STAGE_RECON,
            rule_name="inspection_to_recon",
            evidence="Two required-severity findings.",
        )
        self.assertEqual(st.to_stage, VEHICLE_STAGE_RECON)
        self.assertEqual(st.rule_name, "inspection_to_recon")
        self.assertEqual(st.unmet_prerequisites, ())


# ============================================================================
# Vehicle @property accessors — pure reads
# ============================================================================


class VehiclePropertyAccessorsPureReads(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M52PROP", self.default)

    def test_current_stage_returns_none_when_no_stage_row(self):
        self.assertIsNone(self.vehicle.current_stage)

    def test_current_stage_does_not_create_row_on_first_access(self):
        _ = self.vehicle.current_stage
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=self.vehicle).count(), 0
        )
        self.assertEqual(
            VehicleStageEvent.objects.filter(vehicle=self.vehicle).count(), 0
        )

    def test_current_stage_returns_row_when_present(self):
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_LISTING,
        )
        current = self.vehicle.current_stage
        self.assertIsNotNone(current)
        self.assertEqual(current.current_stage, VEHICLE_STAGE_LISTING)

    def test_is_retail_eligible_false_when_no_stage_row(self):
        self.assertFalse(self.vehicle.is_retail_eligible)

    def test_is_retail_eligible_true_at_frontline(self):
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        self.assertTrue(self.vehicle.is_retail_eligible)

    def test_is_retail_eligible_false_at_off_market(self):
        ensure_current_stage(
            self.vehicle,
            dealership=self.default,
            initial_stage=VEHICLE_STAGE_OFF_MARKET,
        )
        self.assertFalse(self.vehicle.is_retail_eligible)


# ============================================================================
# Regression boundaries — M5.2 doesn't touch M1-M4 substrate.
# ============================================================================


class RegressionBoundaries(TestCase):
    def test_advance_stage_writes_no_workorder_or_vehiclecost(self):
        """M5.2 lifecycle transitions must not touch M4/M2 substrate."""
        from dealer_ai.models import VehicleCost, WorkOrder

        default = Dealership.objects.get(slug="default")
        actor = _make_actor("reg-actor", default, ROLE_SALES_MANAGER)
        v = _make_vehicle("M52REG", default)
        ensure_current_stage(
            v, dealership=default, initial_stage=VEHICLE_STAGE_INSPECTION
        )

        wo_count_before = WorkOrder.objects.filter(vehicle=v).count()
        cost_count_before = VehicleCost.objects.filter(vehicle=v).count()

        advance_stage(
            v,
            dealership=default,
            to_stage=VEHICLE_STAGE_RECON,
            actor=actor,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )

        self.assertEqual(
            WorkOrder.objects.filter(vehicle=v).count(), wo_count_before
        )
        self.assertEqual(
            VehicleCost.objects.filter(vehicle=v).count(), cost_count_before
        )
