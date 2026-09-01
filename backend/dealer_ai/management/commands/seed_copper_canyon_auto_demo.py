"""python manage.py seed_copper_canyon_auto_demo [--reset]

TASK_doors-and-matrix-refresh Part C · sub-item C1 (2026-08-31).
Seeds the demo dealership described in
``docs/_internal/DEMO_READINESS_2026-09-01.md`` §4: one store,
Copper Canyon Auto, coherent operational history, every sidebar
screen non-empty.

Composes existing service verbs — no new models, migrations,
endpoints, or permission classes. Idempotent: re-runs reset the
demo store to canonical state via
``services.demo_store.reset_demo_store`` and rebuild it end-to-
end. The ``--reset`` flag is redundant with the default behavior
and kept only for shape-parity with the ``seed_journey_*``
commands.

Base state comes from the M18.2 ``retail_subprime`` archetype
(20 mixed-make used vehicles, 4 staff, 15 leads, 5 sales
including 1 BHPH, 2 credit apps, 4 follow-up tasks). This
command wraps that with the store name Copper Canyon Auto,
provisions a ``demo-owner`` user, and layers on the demo
extensions the archetype does not cover:

- Distributes vehicles across all 12 ``VehicleStage`` values
  with backdated ``entered_at`` so the aging board reads real.
- Marks 2 in-progress WOs as completed with vendor + actual_cost
  so ``/admin/analytics/vendor-performance/`` returns rows.
- Adds 2 approved WOs with ``authorized_cost`` above the estimate
  — the "awaiting authorization / over budget" pitch screen.
- Extends the BHPH portfolio from 1 note to 3: one current, one
  ~20 days delinquent, one in repossession.
- Builds the F&I chain on both credit apps: one lands in
  ``/admin/f-and-i/deals/`` as a signed contract; the other stays
  in intake with an open Stipulation. A third bare CA keeps
  intake non-trivial.
- Schedules 2 test drives and 1 be-back due today.
- Adds ~30 days of miscellaneous journal entries so the trial
  balance reads like a bookkeeper would recognize.

Verify per the C1 recipe (see ``TASK_doors-and-matrix-
refresh.md`` §C1):

    cd backend
    export M20_ACCEPTANCE_DB=1
    rm -f db.acceptance.sqlite3
    python manage.py migrate --run-syncdb --noinput
    python manage.py seed_copper_canyon_auto_demo
    python manage.py runserver 127.0.0.1:8011 --noreload
    # Log in as demo-owner / demo-owner-password and hit every
    # endpoint behind a sidebar page. None may come back empty.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from dealer_ai.models import (
    BE_BACK_REASON_TEST_DRIVE,
    BHPH_PAYMENT_METHOD_CASH,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_SEVERITY_REQUIRED,
    CONTRACT_TYPE_RISC,
    CREDIT_APP_FORMAT_TABLET,
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    LENDER_SUBMISSION_STATUS_APPROVED,
    LENDER_SUBMISSION_STATUS_PENDING,
    ROLE_DEALER_OWNER,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    SOURCE_AUCTION,
    SOURCE_PRIVATE,
    SOURCE_TRADE,
    STIP_TYPE_PROOF_OF_INCOME,
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
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    VEHICLE_STAGE_WHOLESALE_OUT,
    BhphNote,
    ChatMessage,
    ChatSession,
    ConditionFinding,
    ConditionReport,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealerOnboardingProfile,
    Delivery,
    DealWriteup,
    GLAccount,
    Sale,
    Salesperson,
    UserDealershipRole,
    Vehicle,
    VehicleAcquisition,
    VehicleStage,
    VehicleStageEvent,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.accounting.journal import (
    JournalLineInput,
    post_journal_entry,
)
from dealer_ai.services.be_backs.be_back import record_be_back
from dealer_ai.services.bhph_notes.bhph_note import record_bhph_note
from dealer_ai.services.bhph_payments.bhph_payment import record_payment
from dealer_ai.services.demo_store.registry import (
    create_demo_store,
    reset_demo_store,
)
from dealer_ai.services.demo_store.synthetic_data import synthetic_email
from dealer_ai.services.inventory_import import import_rows
from dealer_ai.services.f_and_i.contract import record_contract, sign_contract
from dealer_ai.services.f_and_i.credit_application import (
    record_credit_application,
)
from dealer_ai.services.f_and_i.deal_structure import record_deal_structure
from dealer_ai.services.f_and_i.funding import record_funding
from dealer_ai.services.f_and_i.lender import (
    record_lender_program,
    record_lender_submission,
)
from dealer_ai.services.f_and_i.stipulation import record_stipulation
from dealer_ai.models import VehicleCost
from dealer_ai.services.deal_writeups.deal_writeup import (
    approve_deal_writeup,
    record_deal_writeup,
)
from dealer_ai.services.delivery.workflow import record_delivery
from dealer_ai.services.sale import record_sale
from dealer_ai.services.lifecycle_aging.snapshots import snapshot_stage_ages
from dealer_ai.services.vendor_sla.detection import detect_sla_breaches
from dealer_ai.services.sale.computation import gross_realized
from dealer_ai.services.vehicle_lifecycle import advance_stage, get_current_stage
from dealer_ai.services.recon import (
    approve_work_order,
    attach_findings,
    complete_work_order,
    create_work_order,
    start_work_order,
)
from dealer_ai.services.repossessions.repossession import record_repossession
from dealer_ai.services.test_drives.test_drive import record_test_drive


User = get_user_model()


STORE_SLUG = "copper-canyon-auto"
STORE_NAME = "Copper Canyon Auto"
DEMO_OWNER_USERNAME = "demo-owner"
DEMO_OWNER_PASSWORD = "demo-owner-password"


# ---------------------------------------------------------------------------
# Stage distribution — all 12 stages populated with realistic aging.
#
# Archetype seeds 20 vehicles (RS-01..RS-20). Three flip to recon
# (RS-04, RS-07, RS-17) during ``_seed_recon``. This extension
# reassigns the remaining 17 across the other 11 stages with plausible
# per-stage aging. Stock numbers are deterministic per the archetype's
# comment; if the archetype ever renames them this table needs a
# refresh.
# ---------------------------------------------------------------------------
_STAGE_PLAN: tuple[tuple[str, tuple[str, ...], int], ...] = (
    # (stage, tuple of stock numbers, days-ago the transition happened)
    #
    # Sold vehicles are NOT forced here. The sale hook in
    # ``services/sale/computation.py::record_sale`` transitions
    # ``frontline → hold_reserved`` on its own for archetype sales
    # (RS-11, RS-12, RS-14, RS-15, RS-16); the mirrored hook in
    # ``_originate_bhph_sale_and_note`` handles the extension BHPH
    # sales (RS-10, RS-13). No entry below picks a sold vehicle —
    # the seed test asserts nothing sold sits on the front line.
    #
    # Every one of the twelve VehicleStage values needs a signal so
    # the aging board reads as a twelve-column story rather than one
    # with silent columns. The lot has 13 unsold vehicles once the
    # 7 sales fire; the plan spreads them across the ten non-sale
    # stages so each carries a plausible resident. RS-06, RS-08 and
    # RS-19 stay at frontline post-plan (unsold aging demo units);
    # RS-07 and RS-17 stay at recon (they back the two awaiting-
    # authorization draft WOs seeded downstream).
    (VEHICLE_STAGE_INCOMING, ("RS-01",), 2),
    (VEHICLE_STAGE_PHOTOGRAPHY, ("RS-02",), 8),
    (VEHICLE_STAGE_INSPECTION, ("RS-03",), 4),
    # RS-04 moves out of the archetype's recon assignment into detail
    # so the aging board's DETAIL column is non-empty. Its recon-era
    # WO history remains valid — WOs are tied to the vehicle, not the
    # current stage.
    (VEHICLE_STAGE_DETAIL, ("RS-04",), 6),
    (VEHICLE_STAGE_QC, ("RS-05",), 7),
    # RS-07, RS-17 stay at recon (archetype) — awaiting-auth draft WOs.
    (VEHICLE_STAGE_LISTING, ("RS-09",), 13),
    # RS-06, RS-08, RS-19 stay at frontline (three unsold aging demo
    # units — a fresh one, one at normal in-market age, one aged past
    # 90 days where an owner starts getting uncomfortable, per
    # ``_FRONTLINE_AGING_DAYS_UNSOLD`` below).
    (VEHICLE_STAGE_COMPANY_USE, ("RS-18",), 100),
    # RS-20 into wholesale_out so the wholesale-out column has a
    # resident. Semantically: a trade-in the lot decided not to
    # retail. RS-19 is no longer forced to off_market — the five
    # delivered sales cover that column via ``_deliver_five_sales``
    # (see below).
    (VEHICLE_STAGE_WHOLESALE_OUT, ("RS-20",), 40),
)


class Command(BaseCommand):
    help = (
        "Seed the Copper Canyon Auto demo dealership (one store, one "
        "persona, coherent history) per TASK_doors-and-matrix-refresh "
        "§C1. Idempotent."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "No-op flag — the command is always idempotent and "
                "always resets the store to canonical state if it "
                "already exists. Kept for shape-parity with the "
                "seed_journey_* commands."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = _provision_store(self.stdout)
            owner = _provision_owner(dealership, self.stdout)
            _provision_onboarding_profile(dealership, self.stdout)
            _distribute_lifecycle_stages(dealership, self.stdout)
            imported_count = _extend_lot_to_target_size(
                dealership, self.stdout
            )
            _expand_stage_distribution(dealership, self.stdout)
            _backdate_frontline_events_for_sales(dealership, self.stdout)
            _normalize_sale_gross(dealership, self.stdout)
            _persona_rename_archetype_rows(dealership, self.stdout)
            completed_vendor_perf = _complete_recon_work_orders(
                dealership, owner, self.stdout
            )
            awaiting_auth = _seed_awaiting_authorization_wos(
                dealership, owner, self.stdout
            )
            bhph_summary = _extend_bhph_portfolio(
                dealership, owner, self.stdout
            )
            fni_summary = _extend_fni_chain(dealership, owner, self.stdout)
            delivered_pks = _deliver_five_sales(dealership, self.stdout)
            extended_sales = _extend_sales_history(
                dealership, owner, self.stdout
            )
            test_drives = _seed_test_drives(dealership, self.stdout)
            be_back = _seed_be_back(dealership, self.stdout)
            journals = _seed_journal_month(dealership, owner, self.stdout)
            # Re-normalize gross_realized after BHPH extension — the
            # two extra BHPH sales originated via _originate_bhph_sale_
            # and_note write Sale rows directly (bypassing record_sale)
            # with gross_realized=0. Rerun the normalizer so every
            # sale posts the $2,000 front gross the analytics screens
            # need to read as believable.
            _normalize_sale_gross(dealership, self.stdout)
            chat_events = _seed_chat_sessions_with_guard_events(
                dealership, self.stdout
            )
            # Second call — catches the two BHPH sales _extend_bhph_
            # portfolio created after the first backdate ran. Idempotent
            # (skips events already dated on-or-before the target).
            _backdate_frontline_events_for_sales(dealership, self.stdout)
            # Aged-loser story: any sold vehicle tagged
            # ``_LOSER_REASON_AGED`` gets its earliest frontline event
            # pushed back to ~105 days ago, so the lifecycle log tells
            # the "sat past 100 days before we cut it" story that the
            # negative gross exists to price. Must run AFTER
            # _backdate_frontline_events_for_sales — that helper
            # overwrites the event to a shorter window (20-44 days).
            _backdate_aged_loser_frontline_events(dealership, self.stdout)
            _backdate_frontline_stage_aging(dealership, self.stdout)
            _backdate_hold_reserved_for_sales(dealership, self.stdout)
            _backdate_off_market_for_deliveries(dealership, self.stdout)
            snapshots = _seed_stage_aging_snapshots(
                dealership, self.stdout
            )
            writeup_pk = _seed_deal_writeup(
                dealership, owner, self.stdout
            )
            sla_wo_pk = _seed_sla_stale_wo(dealership, owner, self.stdout)
            sla_breaches = _materialize_sla_breaches(
                dealership, self.stdout
            )
            estimate_buyer = _seed_buyer_estimate_accuracy(
                dealership, owner, self.stdout
            )

        self.stdout.write(
            self.style.SUCCESS(
                "seed_copper_canyon_auto_demo OK — "
                f"store={dealership.slug!r} name={dealership.name!r}, "
                f"owner={owner.username!r} "
                f"(password={DEMO_OWNER_PASSWORD!r}), "
                f"completed_vendor_perf_wos={completed_vendor_perf}, "
                f"awaiting_authorization_wos={awaiting_auth}, "
                f"imported_extension_vehicles={imported_count}, "
                f"bhph_notes={bhph_summary}, "
                f"fni={fni_summary}, "
                f"delivered_archetype_sale_pks={delivered_pks}, "
                f"extended_sales={extended_sales}, "
                f"test_drives={test_drives}, "
                f"be_back_pk={be_back.pk}, "
                f"manual_journal_entries={journals}, "
                f"chat_sessions={chat_events['sessions']} "
                f"(guard_events={chat_events['guard_events']}), "
                f"stage_aging_snapshots={snapshots}, "
                f"deal_writeup_pk={writeup_pk}, "
                f"sla_stale_wo_pk={sla_wo_pk}, "
                f"sla_breach_records={sla_breaches}, "
                f"buyer_estimate_buyer_id={estimate_buyer}."
            )
        )


# ---------------------------------------------------------------------------
# Store + owner provisioning
# ---------------------------------------------------------------------------


def _provision_store(stdout) -> Dealership:
    """Create the store fresh, or reset an existing one.

    Idempotency: ``reset_demo_store`` deletes every tenanted child row
    keyed to the dealership + every single-tenant demo user, then re-
    runs the archetype builder. The Dealership row itself + its pk
    stay stable so bookmarks work across re-runs.
    """
    existing = Dealership.objects.filter(
        slug=STORE_SLUG, is_demo=True
    ).first()
    if existing is None:
        dealership, summary = create_demo_store(
            slug=STORE_SLUG,
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            name=STORE_NAME,
        )
        stdout.write(
            f"created demo store pk={dealership.pk} slug={STORE_SLUG!r} "
            f"name={STORE_NAME!r}; archetype seeded "
            f"{len(summary.seeded_stock_numbers)} vehicles."
        )
        return dealership

    reset_demo_store(dealership=existing)
    existing.refresh_from_db()
    # Guard against drift in the display name — an operator might
    # have renamed it via the onboarding form between seed runs.
    if existing.name != STORE_NAME:
        existing.name = STORE_NAME
        existing.save(update_fields=["name"])
    stdout.write(
        f"reset existing demo store pk={existing.pk} slug={STORE_SLUG!r} "
        f"name={STORE_NAME!r}."
    )
    return existing


def _provision_owner(dealership: Dealership, stdout):
    """Provision the demo owner user + dealer_owner role membership.

    The archetype's reset path deleted single-tenant demo users, so
    the owner needs re-creation on every re-run. Password rotates to
    the canonical demo value on every re-run so a forgotten test
    change doesn't lock the demo out.
    """
    # Display as Elena Vargas — the Copper Canyon persona owner named
    # in docs/research/INDEPENDENT_DEALER_PIVOT.md §"The persona".
    # username stays `demo-owner` for login-URL stability across seed
    # runs; get_full_name() drives the display everywhere else.
    user, created = User.objects.get_or_create(
        username=DEMO_OWNER_USERNAME,
        defaults={
            "email": "elena@coppercanyonauto.example",
            "first_name": "Elena",
            "last_name": "Vargas",
        },
    )
    # Re-runs (get path) need the display fields synced to the persona
    # even if the row already existed, in case a prior seed left
    # "Demo Owner" on it.
    if not created:
        user.email = "elena@coppercanyonauto.example"
        user.first_name = "Elena"
        user.last_name = "Vargas"
    user.set_password(DEMO_OWNER_PASSWORD)
    user.is_active = True
    user.save()
    UserDealershipRole.objects.get_or_create(
        user=user,
        dealership=dealership,
        defaults={"role": ROLE_DEALER_OWNER},
    )
    verb = "created" if created else "reused"
    stdout.write(
        f"{verb} owner user {user.username!r} with dealer_owner role "
        f"at {dealership.slug!r}."
    )
    return user


# ---------------------------------------------------------------------------
# Onboarding profile — the /dealer-ai-onboarding endpoint reads
# DealerOnboardingProfile, not Dealership.name; without a profile the
# store label on the sidebar reads blank.
# ---------------------------------------------------------------------------


def _provision_onboarding_profile(dealership: Dealership, stdout) -> None:
    """Ensure a DealerOnboardingProfile exists for the store with the
    Copper Canyon Auto branding populated.

    The onboarding view reads the first profile scoped to the current
    tenant. Without this, the sidebar renders the display name as an
    empty string even though ``Dealership.name`` is set.
    """
    # Persona per docs/research/INDEPENDENT_DEALER_PIVOT.md §"The
    # persona — Copper Canyon Auto": Elena Vargas, second generation,
    # her dad Manuel founded the lot in 1987. Voice is warm, practical,
    # bilingual-friendly, low-pressure, credit-inclusive.
    profile, created = DealerOnboardingProfile.objects.get_or_create(
        dealership=dealership,
        defaults={
            "dealership_name": STORE_NAME,
            "store_location": "1420 Frontage Rd, Yuma, AZ 85364",
            "main_brands": "Ford, Chevrolet, Toyota, Honda — mixed used",
            "sales_phone": "928-555-0100",
            "website": "https://coppercanyonauto.example",
            "sales_tone": (
                "warm, practical, bilingual-friendly, low-pressure, "
                "credit-inclusive"
            ),
            "pricing_comfort": "post-price on the frontline",
            "appointment_preference": "same-day when possible",
            "lead_handoff_style": "warm handoff by name",
            "salesperson_name": "Elena Vargas",
            "salesperson_role": "Owner (second-generation; est. 1987)",
            "salesperson_phone": "928-555-0100",
            "salesperson_email": "elena@coppercanyonauto.example",
        },
    )
    # Re-runs after reset find no profile (reset cleared it), so the
    # get_or_create path above creates it. This branch handles the
    # unlikely case an operator edited the profile between runs — we
    # keep their edits and only sync the display name so the sidebar
    # stays consistent with the demo persona.
    if not created and profile.dealership_name != STORE_NAME:
        profile.dealership_name = STORE_NAME
        profile.save(update_fields=["dealership_name"])
    verb = "created" if created else "reused"
    stdout.write(
        f"{verb} onboarding profile for {dealership.slug!r} "
        f"(dealership_name={STORE_NAME!r})."
    )


# ---------------------------------------------------------------------------
# Lifecycle stage distribution — 12 stages populated with real aging
# ---------------------------------------------------------------------------


def _distribute_lifecycle_stages(dealership: Dealership, stdout) -> None:
    """Reassign vehicles to spread across all 12 VehicleStage values.

    The archetype leaves 17 vehicles at ``frontline`` and 3 at
    ``recon``. Analytics that read the aging board need signal at
    every stage; this walks ``_STAGE_PLAN`` and rewrites
    ``VehicleStage`` + appends a matching ``VehicleStageEvent`` per
    vehicle. The three recon vehicles are left alone.

    The C1 review (2026-09-01) flagged out-of-order event logs: the
    archetype's bootstrap event lands at ``entered_at=now`` (the
    contract enforced by ``vehicle_lifecycle.bootstrap_vehicle_stage``
    is that the stage row and its bootstrap event share the same
    timestamp — see migration 0017). When this seed then backdates
    the stage row to N days ago and appends a manual transition
    dated N days ago, the vehicle's event log reads bootstrap-at-now
    followed by manual-at-(now - N days) — the audit trail runs
    backwards. Fix: backdate the pre-existing bootstrap event to
    predate the manual transition being written here, so the log
    reads bootstrap → manual in the order the timestamps say it did.
    """
    now = timezone.now()
    reassigned = 0
    for stage_key, stocks, days_ago in _STAGE_PLAN:
        entered_at = now - dt.timedelta(days=days_ago)
        for stock in stocks:
            try:
                vehicle = Vehicle.objects.get(
                    dealership=dealership, stock_number=stock
                )
            except Vehicle.DoesNotExist:  # archetype drift guard
                stdout.write(
                    f"  skip: stock={stock!r} not present after "
                    "archetype build."
                )
                continue

            stage_row = VehicleStage.objects.get(vehicle=vehicle)
            previous_stage = stage_row.current_stage
            if previous_stage == stage_key:
                # Already correct (e.g. recon targets asked to stay).
                continue
            # Backdate the bootstrap event(s) for this vehicle so no
            # event in the log post-dates the manual transition being
            # written next. Add a ~15-day cushion so the bootstrap
            # reads as "arrived on the lot before we moved it through
            # the pipeline." Uses a filter().update() so the timestamp
            # is written directly (VehicleStageEvent.entered_at has no
            # auto_now_add, so a straight write suffices, but .update
            # scopes cleanly).
            bootstrap_entered_at = entered_at - dt.timedelta(days=15)
            VehicleStageEvent.objects.filter(
                vehicle=vehicle,
                trigger="bootstrap",
                entered_at__gte=entered_at,
            ).update(entered_at=bootstrap_entered_at)
            stage_row.current_stage = stage_key
            stage_row.entered_at = entered_at
            stage_row.trigger = VEHICLE_STAGE_TRIGGER_MANUAL
            stage_row.save(
                update_fields=["current_stage", "entered_at", "trigger"]
            )
            VehicleStageEvent.objects.create(
                dealership=dealership,
                vehicle=vehicle,
                from_stage=previous_stage,
                to_stage=stage_key,
                entered_at=entered_at,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
                notes="Copper Canyon demo seed — spread across 12 stages.",
            )
            reassigned += 1
    stdout.write(
        f"distributed lifecycle stages: reassigned {reassigned} vehicle(s) "
        f"across {len(_STAGE_PLAN)} stage rows (recon left as archetype)."
    )


# ---------------------------------------------------------------------------
# Inventory-turn support — ensure every sold vehicle has a frontline
# VehicleStageEvent that predates its sale_date, so
# services.analytics.lifecycle_aging.inventory_turn returns non-zero
# days-to-sale instead of "no signal."
# ---------------------------------------------------------------------------


def _backdate_frontline_events_for_sales(
    dealership: Dealership, stdout
) -> None:
    """For every Sale, ensure a ``to_stage=frontline`` VehicleStageEvent
    exists with ``entered_at`` earlier than ``sale_date``.

    ``inventory_turn`` computes days-to-sale as
    ``sale_date - earliest_frontline_event.entered_at``. Vehicles
    without any frontline event, or with one dated after the sale,
    are skipped entirely (see
    ``services.analytics.lifecycle_aging.inventory_turn`` §Notes).
    The archetype's sold vehicles are bootstrapped at frontline via a
    signal that stamps ``entered_at=now`` — which is later than every
    sale_date and so skipped. Backdate them by 20-30 days per vehicle
    so the aggregation reads a plausible distribution.
    """
    backdated = 0
    for sale in Sale.objects.filter(dealership=dealership).select_related(
        "vehicle"
    ):
        vehicle = sale.vehicle
        # Days between the desired frontline entry and the sale —
        # varies across vehicles so the days-to-sale distribution has
        # spread, not a single value.
        days_before_sale = 20 + (sale.pk * 3) % 25
        target_entered_at = (
            dt.datetime.combine(
                sale.sale_date, dt.time(9, 0), tzinfo=dt.timezone.utc
            )
            - dt.timedelta(days=days_before_sale)
        )
        # Prefer to update an existing frontline event if there is one
        # dated after target; otherwise create a fresh one. Either way
        # the earliest-frontline read now falls before sale_date.
        existing_frontline = (
            VehicleStageEvent.objects.filter(
                vehicle=vehicle, to_stage=VEHICLE_STAGE_FRONTLINE
            )
            .order_by("entered_at")
            .first()
        )
        if (
            existing_frontline is not None
            and existing_frontline.entered_at <= target_entered_at
        ):
            continue  # already good — earliest event predates sale
        if existing_frontline is not None:
            existing_frontline.entered_at = target_entered_at
            existing_frontline.save(update_fields=["entered_at"])
        else:
            VehicleStageEvent.objects.create(
                dealership=dealership,
                vehicle=vehicle,
                from_stage="",
                to_stage=VEHICLE_STAGE_FRONTLINE,
                entered_at=target_entered_at,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
                notes=(
                    "Copper Canyon demo seed — backdated so "
                    "inventory-turn has a days-to-sale reference."
                ),
            )
        backdated += 1
    stdout.write(
        f"backdated {backdated} frontline event(s) for sold vehicles "
        "so inventory-turn returns real days-to-sale."
    )


# ---------------------------------------------------------------------------
# Frontline aging — spread VehicleStage.entered_at so the aging board
# reads a real distribution instead of a flat line at zero.
# ---------------------------------------------------------------------------

# Days-ago pattern for unsold frontline vehicles. Chosen so the p50
# reads as a plausible aging distribution: one unit under a week
# (fresh), one around a month (normal), one past 90 days (aged out —
# wholesale or drop the price). The 2026-08-31 competitive teardown
# named the aging board as one of two capabilities absent from every
# competitor; a flat-at-zero read renders it useless.
_FRONTLINE_AGING_DAYS_UNSOLD: tuple[int, ...] = (
    3, 6, 10, 15, 22, 32, 45, 60, 78, 100,
)


def _backdate_frontline_stage_aging(
    dealership: Dealership, stdout
) -> None:
    """Spread ``VehicleStage.entered_at`` across unsold frontline
    vehicles so the aging board reads a real distribution instead of
    a flat line at zero.

    Sold vehicles do not appear on the front line — the sale hook in
    ``services/sale/computation.py::record_sale`` transitions
    ``frontline → hold_reserved`` on its own, and the extension
    helper ``_originate_bhph_sale_and_note`` mirrors that transition
    for its model-direct sales. Anything at frontline here is unsold
    by construction; a sold-frontline row would be a bug that the
    seed test asserts against.

    Runs BEFORE ``_seed_stage_aging_snapshots``. The 15-day snapshot
    backfill reads current state, so every stage row's ``entered_at``
    must be at its intended value before the loop starts.

    Also backdates any ``trigger="bootstrap"`` :class:`VehicleStageEvent`
    that would post-date the newly-written ``entered_at``, so the
    vehicle's stage-event log stays in chronological order (same
    invariant ``_distribute_lifecycle_stages`` protects for the
    stages it reassigns).
    """
    now = timezone.now()
    frontline_rows = list(
        VehicleStage.objects.filter(
            dealership=dealership,
            current_stage=VEHICLE_STAGE_FRONTLINE,
        )
        .select_related("vehicle")
        .order_by("vehicle__stock_number")
    )
    updated = 0
    for offset, stage_row in enumerate(frontline_rows):
        vehicle = stage_row.vehicle
        days_ago = _FRONTLINE_AGING_DAYS_UNSOLD[
            offset % len(_FRONTLINE_AGING_DAYS_UNSOLD)
        ]
        new_entered_at = now - dt.timedelta(days=days_ago)
        VehicleStageEvent.objects.filter(
            vehicle=vehicle,
            trigger="bootstrap",
            entered_at__gt=new_entered_at,
        ).update(
            entered_at=new_entered_at - dt.timedelta(hours=1)
        )
        stage_row.entered_at = new_entered_at
        stage_row.save(update_fields=["entered_at"])
        updated += 1
    stdout.write(
        f"backdated {updated} unsold frontline VehicleStage row(s) "
        f"across {list(_FRONTLINE_AGING_DAYS_UNSOLD)!r} days-ago."
    )


def _backdate_hold_reserved_for_sales(
    dealership: Dealership, stdout
) -> None:
    """Set ``VehicleStage.entered_at`` on each sold vehicle sitting at
    ``hold_reserved`` to the sale date, so the aging board reads real
    days-since-sale instead of a flat zero.

    The sale hook in ``services/sale/computation.py::record_sale``
    transitions the vehicle into ``hold_reserved`` at ~now (hook time),
    which leaves the aging read flat. In real operation the hold
    starts when the sale is booked, so anchoring the stage_row's
    ``entered_at`` to ``sale_date`` gives a truthful demo reading.

    Runs BEFORE ``_seed_stage_aging_snapshots``. Only touches the
    stage row's ``entered_at`` — the paired hook event's ``entered_at``
    is left at hook time so the log-not-backwards invariant remains
    (latest event's ``to_stage`` still equals ``current_stage``).
    """
    updated = 0
    rows = list(
        VehicleStage.objects.filter(
            dealership=dealership,
            current_stage=VEHICLE_STAGE_HOLD_RESERVED,
        ).select_related("vehicle")
    )
    for stage_row in rows:
        sale = Sale.objects.filter(vehicle=stage_row.vehicle).first()
        if sale is None:
            continue
        new_entered_at = dt.datetime.combine(
            sale.sale_date, dt.time(9, 0), tzinfo=dt.timezone.utc
        )
        stage_row.entered_at = new_entered_at
        stage_row.save(update_fields=["entered_at"])
        updated += 1
    stdout.write(
        f"backdated {updated} sold hold_reserved VehicleStage row(s) "
        f"to their sale date."
    )


# ---------------------------------------------------------------------------
# Delivery — deliver five of the seven sold vehicles so the lot reads
# like a working store, leaving two at ``hold_reserved`` as *sold,
# awaiting funding*.
# ---------------------------------------------------------------------------

# Stock numbers of the two sales that stay at ``hold_reserved`` after
# the delivery pass — matched by the F&I chain the seed builds:
#
# - RS-15 has a signed RISC contract with ``record_funding`` recording
#   the packet submitted to the lender; the wire has not landed. Every
#   independent dealer has one of these on the desk right now.
# - RS-16 has an open :class:`Stipulation` waiting on the customer's
#   proof of income; the lender has not approved yet. The other
#   half of the "sold-but-not-off-the-lot" pair.
#
# Everything else — RS-10, RS-11, RS-12, RS-13, RS-14 — is delivered.
_SALES_STAYING_AT_HOLD_RESERVED: tuple[str, ...] = ("RS-15", "RS-16")

# Days-after-sale-date to record delivery, spread so the off_market
# aging column reads a real distribution rather than a flat line at
# zero. Applied by stock-number ordering across the five delivered
# vehicles.
_DELIVERY_DAYS_AFTER_SALE: tuple[int, ...] = (2, 3, 5, 8, 12)


def _deliver_five_sales(
    dealership: Dealership, stdout
) -> list[int]:
    """Record :class:`Delivery` for five of the seven sales via the real
    :func:`services.delivery.workflow.record_delivery` path.

    Composes the shipped delivery verb; the SESSION_223 hook then
    advances ``hold_reserved → off_market`` on each delivered vehicle.
    Leaves ``_SALES_STAYING_AT_HOLD_RESERVED`` at ``hold_reserved`` so
    the aging board still reads a resident in that stage — the demo's
    "sold, awaiting funding" story.

    Idempotent — ``record_delivery`` refuses a second Delivery on a
    Sale that already has one. The retry path here skips those sales.
    """
    sales = list(
        Sale.objects.filter(dealership=dealership).select_related("vehicle")
    )
    to_deliver = [
        sale
        for sale in sales
        if sale.vehicle.stock_number not in _SALES_STAYING_AT_HOLD_RESERVED
    ]
    # Deterministic order — sort by sale_date descending so the newest
    # sale gets the shortest delivery lag. That mirrors real operation
    # (a lot delivers a fresh sale in a couple of days) and keeps every
    # delivery date in the past even against a very recent sale.
    to_deliver.sort(key=lambda s: (s.sale_date, s.vehicle.stock_number), reverse=True)

    today = timezone.now().date()
    yesterday = today - dt.timedelta(days=1)
    delivered_sale_pks: list[int] = []
    for offset, sale in enumerate(to_deliver):
        if Delivery.objects.filter(sale=sale).exists():
            delivered_sale_pks.append(sale.pk)
            continue
        days_after = _DELIVERY_DAYS_AFTER_SALE[
            offset % len(_DELIVERY_DAYS_AFTER_SALE)
        ]
        delivery_date = sale.sale_date + dt.timedelta(days=days_after)
        # Cap at yesterday — a demo shouldn't show a future delivery
        # for a sale that already booked. Cheap belt-and-suspenders for
        # the newest sales, whose sale_date + delta can land past today.
        if delivery_date > yesterday:
            delivery_date = yesterday
        record_delivery(
            sale.vehicle,
            dealership=dealership,
            delivery_date=delivery_date,
            temp_tag_number=f"TT-{sale.vehicle.stock_number}",
            notes=(
                "Copper Canyon demo seed — delivered via record_delivery; "
                "hook advances hold_reserved → off_market."
            ),
        )
        delivered_sale_pks.append(sale.pk)
    stdout.write(
        f"delivered {len(delivered_sale_pks)} of {len(sales)} sale(s); "
        f"remainder sit at hold_reserved as sold-awaiting-funding "
        f"(kept: {list(_SALES_STAYING_AT_HOLD_RESERVED)!r})."
    )
    return delivered_sale_pks


def _backdate_off_market_for_deliveries(
    dealership: Dealership, stdout
) -> None:
    """Set ``VehicleStage.entered_at`` on each delivered sold vehicle to
    its :attr:`Delivery.delivery_date`, so the aging board reads real
    days-since-delivery instead of hook-time (~now).

    Analogue of :func:`_backdate_hold_reserved_for_sales` for the
    off_market column. Only touches sold vehicles with a matching
    :class:`Delivery` — leaves the two unsold off_market residents
    (if any survive in ``_STAGE_PLAN``) untouched.

    Runs BEFORE :func:`_seed_stage_aging_snapshots`. Only the stage
    row's ``entered_at`` moves — the paired hook event's ``entered_at``
    stays at hook time so the log-not-backwards invariant holds
    (latest event's ``to_stage`` still equals ``current_stage``).
    """
    updated = 0
    for delivery in Delivery.objects.filter(
        dealership=dealership
    ).select_related("sale__vehicle"):
        vehicle = delivery.sale.vehicle
        if delivery.delivery_date is None:
            continue
        stage_row = VehicleStage.objects.filter(
            dealership=dealership,
            vehicle=vehicle,
            current_stage=VEHICLE_STAGE_OFF_MARKET,
        ).first()
        if stage_row is None:
            continue
        stage_row.entered_at = dt.datetime.combine(
            delivery.delivery_date,
            dt.time(9, 0),
            tzinfo=dt.timezone.utc,
        )
        stage_row.save(update_fields=["entered_at"])
        updated += 1
    stdout.write(
        f"backdated {updated} delivered off_market VehicleStage row(s) "
        f"to their delivery date."
    )


# ---------------------------------------------------------------------------
# Sale gross normalization — every sale posts a plausible front gross
# ---------------------------------------------------------------------------


def _normalize_sale_gross(dealership: Dealership, stdout) -> None:
    """Work around the archetype's acquisition-basis double-count so the
    gross-profit endpoints do not report the store losing money on
    every retail sale.

    The C1 review's original diagnosis was wrong (see task file's
    Correction section, 2026-09-01). The real defect lives in
    ``services/demo_store/archetypes/retail_subprime.py`` `_seed_sales`
    — for every Sale it posts a `VehicleCost(category=parts,
    vendor="Acquisition basis for ...")` row that carries the same
    purchase_price the parent :class:`VehicleAcquisition` already
    holds. `services/vehicle_ledger.py` sums acquisition + recon
    (including parts) into ``total_investment``, so the acquisition
    price gets counted twice, gross reads negative by roughly the
    purchase price, and the recon-cost-per-source analytics
    mis-attribute the acquisition as a $5,500-mean "parts" spend.

    This function papers over that defect for the demo store only:

    1. Delete the "Acquisition basis for X" VehicleCost rows the
       archetype double-posts, so ``total_investment`` reflects the
       parent :class:`VehicleAcquisition` alone.
    2. Also delete "Acquisition basis" duplicates on any Sale
       originated by ``_originate_bhph_sale_and_note`` further down
       the seed pipeline (defensive — that helper does not create
       them today, but the same rule applies if it ever does).
    3. Recompute :attr:`Sale.gross_realized` for every Sale via
       :func:`services.sale.computation.gross_realized`, so the
       denormalized column reads the corrected number the analytics
       endpoints will show.

    Called twice from ``handle()`` — once after archetype sales, once
    after BHPH extension sales — so the second pass catches the two
    BHPH-originated Sales the first pass missed.

    **Product-code defect, not fixed here.** The archetype double-
    count also lands in prod for any dealer whose seed inherits the
    same shape; ``docs/_internal/TASK_archetype_acquisition_
    double_count.md`` tracks it. Do not fix
    ``retail_subprime.py`` inside this task — Non-goal amended
    2026-09-01 keeps ``services/demo_store/`` out of bounds.
    """
    duplicate_qs = VehicleCost.objects.filter(
        dealership=dealership,
        vendor__startswith="Acquisition basis for",
    )
    deleted, _ = duplicate_qs.delete()
    updated = 0
    for sale in Sale.objects.filter(dealership=dealership).select_related(
        "vehicle"
    ):
        sale.gross_realized = gross_realized(sale)
        sale.save(update_fields=["gross_realized"])
        updated += 1
    stdout.write(
        f"normalized gross_realized on {updated} sale(s) "
        f"(deleted {deleted} archetype-double-counted VehicleCost row(s))."
    )


# ---------------------------------------------------------------------------
# Persona rename — strip archetype "(demo)" markers from rows that
# will show up on customer-facing screens.
# ---------------------------------------------------------------------------


# Yuma-shaped names for the four archetype-created Salesperson rows.
# Match by existing name (not SYNTHETIC_NAMES index) so a future
# reordering of ``synthetic_names.py`` breaks loudly at import-time
# (KeyError-shaped) rather than silently swapping which row gets which
# name. Salesperson.slug stays stable — the Team page shows Name, but
# the M4C advisor-scoping permission classes key on user identity.
_ARCHETYPE_SALESPERSON_RENAMES: dict[str, str] = {
    "Alexis Testworth": "Miguel Ortega",
    "Avery Mockington": "Ashley Nguyen",
    "Jamie Demoson": "Rafael Herrera",
    "Morgan Fictionton": "Danielle Kim",
}

# Yuma-shaped names for the archetype's CustomerLead rows — the 15
# leads from _seed_leads plus the 5 buyer leads from _seed_sales.
# Names picked for the Copper Canyon persona (Yuma, AZ — border town,
# mixed Anglo + Hispanic). Consistent with the seed's own extensions
# (Elena Vargas, Marcus Delgado, Priya Alvarez).
_ARCHETYPE_LEAD_RENAMES: dict[str, str] = {
    # Leads (SYNTHETIC_NAMES 10..24).
    "Blake Simulton": "Carlos Reyes",
    "Cameron Practiceworth": "Sofia Mendoza",
    "Drew Rehearsalson": "Anthony Torres",
    "Emerson Scenariofield": "Isabella Ruiz",
    "Finley Storybrook": "David Lam",
    "Harper Draftly": "Maria Contreras",
    "Indigo Sketchford": "Julio Salazar",
    "Kai Blueprintworth": "Jasmine Ford",
    "Logan Prototypeton": "Sebastian Cortez",
    "Maddox Diagrammer": "Alicia Vega",
    "Nolan Fixturely": "Tomas Guerrero",
    "Oakley Sandboxson": "Beatriz Molina",
    "Parker Rehearsalworth": "Nathan Chavez",
    "Quincy Stubfield": "Vanessa Padilla",
    "Rowan Blankspace": "Gabriel Ortiz",
    # Buyers created by _seed_sales (SYNTHETIC_NAMES 25..29).
    "Sawyer Placeholderfield": "Ricardo Navarro",
    "Tatum Testflight": "Angela Vasquez",
    "Umbria Rehearsalton": "Christian Aguilar",
    "Vale Dryrunson": "Monica Solis",
    "Wren Trialbrook": "Ernesto Duarte",
}


def _persona_rename_archetype_rows(
    dealership: Dealership, stdout
) -> None:
    """Rename archetype-created rows so the persona-facing demo screens
    do not read as an obvious test fixture.

    The Copper Canyon persona is documented in
    ``docs/research/INDEPENDENT_DEALER_PIVOT.md`` (Yuma, AZ —
    independent, mixed-make used lot, credit-inclusive, bilingual-
    friendly). Consistency with the persona doc beats the archetype's
    tester-safety naming for rows that show up on the demo's own
    screens.

    Three renames — vendor, salesperson, lead:

    - **Vendors.** Any vendor whose ``name`` ends with ``(demo)``
      gets the suffix stripped. Also normalizes their
      ``@demo.dealer-ai.example`` emails to the ``.example`` short
      form so the vendor list reads clean.
    - **Salespeople.** The four archetype-created rows
      (:data:`_ARCHETYPE_SALESPERSON_RENAMES`) get Yuma-shaped names
      via a local override. The linked :class:`User`'s
      ``first_name`` / ``last_name`` / ``email`` follow. The
      ``username`` stays stable (``<dealership.slug>-<slug>``) so the
      login credentials the demo owner recorded still work; the
      Salesperson ``slug`` stays stable so ``advisor-*`` references
      throughout the seed do not need to be re-plumbed. Only the
      display-facing fields change.
    - **Customer leads.** The 15 leads plus 5 buyer leads seeded
      through :data:`services.demo_store.synthetic_names.SYNTHETIC_NAMES`
      get renamed via :data:`_ARCHETYPE_LEAD_RENAMES`, with emails
      recomputed through :func:`synthetic_email`. Only rows whose
      current name matches a key in the map are touched — the seed's
      own extensions (Elena Vargas / Marcus Delgado / Priya Alvarez
      via ``_originate_bhph_sale_and_note`` / ``_extend_fni_chain``)
      stay untouched because they were already Yuma-shaped.

    Deliberately does **not** touch
    :data:`services/demo_store/synthetic_names.py` (per
    TASK_c11-demo-seed-truthfulness.md non-goal): the
    ``Testworth`` / ``Rehearsalton`` convention there is the M18.1
    tester-safety doctrine and still governs archetype-internal
    fixtures and every acceptance test. The persona-override happens
    inside this seed, not in the shared roster.

    Idempotent — the second pass finds already-renamed rows because
    match is on the current name string; renamed rows will not
    match a key in the maps and are skipped.
    """
    demo_suffix_vendors = Vendor.objects.filter(
        dealership=dealership, name__endswith=" (demo)"
    )
    renamed_vendors = 0
    for vendor in demo_suffix_vendors:
        vendor.name = vendor.name[: -len(" (demo)")]
        # Also clean up ``@demo.dealer-ai.example`` email suffixes on
        # the same rows for consistency.
        if vendor.email.endswith("@demo.dealer-ai.example"):
            vendor.email = vendor.email.replace(
                "@demo.dealer-ai.example", ".example"
            )
        vendor.save(update_fields=["name", "email"])
        renamed_vendors += 1

    renamed_salespeople = 0
    for salesperson in Salesperson.objects.filter(
        dealership=dealership,
        name__in=list(_ARCHETYPE_SALESPERSON_RENAMES.keys()),
    ).select_related("user"):
        new_name = _ARCHETYPE_SALESPERSON_RENAMES[salesperson.name]
        salesperson.name = new_name
        salesperson.save(update_fields=["name"])
        user = salesperson.user
        if user is not None:
            first, _, last = new_name.partition(" ")
            user.first_name = first
            user.last_name = last
            user.email = synthetic_email(new_name)
            user.save(update_fields=["first_name", "last_name", "email"])
        renamed_salespeople += 1

    renamed_leads = 0
    for lead in CustomerLead.objects.filter(
        dealership=dealership,
        name__in=list(_ARCHETYPE_LEAD_RENAMES.keys()),
    ):
        new_name = _ARCHETYPE_LEAD_RENAMES[lead.name]
        lead.name = new_name
        lead.email = synthetic_email(new_name)
        lead.save(update_fields=["name", "email"])
        renamed_leads += 1

    stdout.write(
        f"persona-renamed archetype rows: "
        f"vendors={renamed_vendors} (stripped '(demo)'), "
        f"salespeople={renamed_salespeople}, "
        f"leads={renamed_leads}."
    )


# ---------------------------------------------------------------------------
# Recon — complete some WOs so vendor-performance analytics has signal
# ---------------------------------------------------------------------------


def _complete_recon_work_orders(
    dealership: Dealership, owner, stdout
) -> int:
    """Advance 2 archetype WOs to ``completed`` with actual_cost.

    Vendor-performance analytics filters to
    ``status=completed AND venue=outsourced AND vendor IS NOT NULL``
    (see ``services.analytics.recon.vendor_performance``). The
    archetype leaves all WOs at ``in_progress``, so the endpoint
    returns an empty list. This flips the first two to ``completed``
    with a plausible ``actual_cost`` slightly above the estimated
    parts sum, so the variance-pct metric has non-zero signal.
    """
    now = timezone.now()
    completed = 0
    outsourced_wos = list(
        WorkOrder.objects.filter(
            dealership=dealership,
            status="in_progress",
            venue="outsourced",
            vendor__isnull=False,
        ).order_by("pk")[:2]
    )
    for offset, wo in enumerate(outsourced_wos):
        # Backfill an estimated_cost on the WO (archetype leaves it
        # null). buyer_estimate_accuracy requires both estimated and
        # actual cost to compute variance; without an estimate, the
        # completed WO drops out of the accuracy computation. Pick a
        # number 10% under the actual so the variance-pct reads as
        # "buyer estimated tight, actual ran a bit over" — the shape
        # a real buyer's early-window accuracy chart wants.
        estimated_cost = Decimal("560.00") + Decimal(offset * 40)
        WorkOrder.objects.filter(pk=wo.pk).update(
            estimated_cost=estimated_cost
        )
        wo.refresh_from_db()
        actual_cost = Decimal("620.00") + Decimal(offset * 40)
        complete_work_order(
            wo,
            dealership=dealership,
            completed_by=owner,
            actual_cost=actual_cost,
            actual_completion_date=(now - dt.timedelta(days=1)).date(),
        )
        completed += 1
    stdout.write(
        f"completed {completed} outsourced WO(s) for vendor-performance "
        "analytics."
    )
    return completed


# ---------------------------------------------------------------------------
# Recon — the pitch: 2 WOs awaiting authorization, over budget
# ---------------------------------------------------------------------------


def _seed_awaiting_authorization_wos(
    dealership: Dealership, owner, stdout
) -> int:
    """Create 2 WOs that sit at ``draft`` with an ``estimated_cost``
    that lands above what an owner would authorize — the "awaiting
    authorization / over budget" screen the task calls the pitch.

    The C1 review (2026-09-01) flagged the original implementation:
    it called ``approve_work_order`` and then set
    ``authorized_cost > estimated_cost``, which reads as *"somebody
    already authorized more than was estimated,"* the opposite of the
    story. Per ``services/recon.py:1056``, ``approve_work_order``
    transitions ``draft → approved`` — so a work order waiting on a
    human is ``draft``. Leave these in draft; the pitch screen is
    the queue of drafts with over-budget estimates.

    Uses one of the archetype's recon vehicles as the parent so
    there is already a condition report + findings to attach.
    Category = ``mechanical`` matches the archetype pattern.
    """
    now = timezone.now()
    # Vendor for the outsourced awaiting-authorization work — a
    # second vendor beyond the archetype's Desert Auto Repair so the
    # vendor list on ``/dealer-ai-admin`` reads more than a single row.
    vendor = Vendor.objects.create(
        dealership=dealership,
        name="Yuma Transmission Specialists",
        slug="yuma-transmission-specialists",
        categories=["mechanical"],
        phone="928-555-0142",
        email="dispatch@yumatransmission.example",
        is_active=True,
    )

    # Pick two recon vehicles that already have condition findings.
    # Recon-in-progress vehicles from archetype: RS-04, RS-07, RS-17.
    # RS-04 already has an outsourced in_progress WO from the archetype,
    # so use RS-07 and RS-17 for the new awaiting-authorization WOs.
    target_stocks = ("RS-07", "RS-17")
    created_count = 0
    for offset, stock in enumerate(target_stocks):
        try:
            vehicle = Vehicle.objects.get(
                dealership=dealership, stock_number=stock
            )
        except Vehicle.DoesNotExist:
            stdout.write(
                f"  skip awaiting-auth WO: stock={stock!r} missing."
            )
            continue
        findings = list(
            ConditionFinding.objects.filter(
                report__vehicle=vehicle
            ).order_by("pk")
        )
        if not findings:
            stdout.write(
                f"  skip awaiting-auth WO for {stock!r}: no findings."
            )
            continue

        # Estimate lands above what an owner would authorize on a
        # $8-12k retail unit — the whole point of the screen is
        # *the money stops here until a human says yes*.
        estimated_cost = Decimal("1450.00") + Decimal(offset * 220)
        wo = create_work_order(
            vehicle,
            dealership=dealership,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue="outsourced",
            vendor=vendor,
            estimated_cost=estimated_cost,
            notes=(
                "Estimate came in above the recon budget — needs owner "
                "authorization before we release the work."
            ),
        )
        # attach_findings requires the WO in draft — which is where it
        # stays. Leaving the WO unapproved is the pitch: this is what
        # a draft awaiting authorization looks like in the queue.
        attach_findings(
            wo,
            dealership=dealership,
            finding_ids=[findings[0].pk],
        )
        # Backdate the created_at so the aging read is not "0 minutes"
        # — the owner should see the estimate has been sitting for
        # roughly a day, not that it just arrived. Uses .update() to
        # bypass auto_now_add on the field.
        WorkOrder.objects.filter(pk=wo.pk).update(
            created_at=now - dt.timedelta(hours=8 + offset * 4)
        )
        created_count += 1
    stdout.write(
        f"seeded {created_count} awaiting-authorization / over-budget WO(s)."
    )
    return created_count


# ---------------------------------------------------------------------------
# BHPH portfolio — 3 notes at 3 different lifecycle states
# ---------------------------------------------------------------------------


def _extend_bhph_portfolio(
    dealership: Dealership, owner, stdout
) -> dict:
    """Extend the archetype's 1 BHPH note to a 3-note book.

    The task's C1 output contract wants "one current note, one about
    20 days down, one in repossession." The archetype originates one
    note against RS-14 (BHPH sale). This creates two more by
    originating BHPH-finance-type sales on two frontline vehicles,
    then applies payment history / repossession accordingly.

    Returns a summary dict of the three notes' pks + state.
    """
    now = timezone.now()

    # The archetype's existing note. Mark it "current" — apply a
    # recent payment so the delinquency read stays green.
    archetype_note = BhphNote.objects.filter(
        dealership=dealership, sale__vehicle__stock_number="RS-14"
    ).first()
    if archetype_note is not None:
        record_payment(
            dealership=dealership,
            note=archetype_note,
            paid_at=now - dt.timedelta(days=3),
            amount=Decimal("165.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )

    # Second note — ~20 days delinquent. New BHPH sale against an
    # inventory vehicle that has not yet sold, then originate the
    # note and skip payments so the delinquency counter reads real.
    delinquent_note = _originate_bhph_sale_and_note(
        dealership=dealership,
        stock="RS-13",
        buyer_name="Marcus Delgado",
        buyer_email="marcus.delgado@demo.dealer-ai.example",
        buyer_phone="555-0187",
        days_ago_sold=45,
        first_payment_days_ago=25,  # payment was due 25 days ago
    )
    # Deliberately no payment recorded → delinquency read shows
    # ~20 days past first_payment_due.

    # Third note — in repossession. New BHPH sale, note, then
    # ``record_repossession`` to move it into the repossession state.
    repo_note = _originate_bhph_sale_and_note(
        dealership=dealership,
        stock="RS-10",
        buyer_name="Priya Alvarez",
        buyer_email="priya.alvarez@demo.dealer-ai.example",
        buyer_phone="555-0193",
        days_ago_sold=90,
        first_payment_days_ago=70,
    )
    if repo_note is not None:
        record_repossession(
            dealership=dealership,
            note=repo_note,
            ordered_at=now - dt.timedelta(days=5),
            agent_name="Sonoran Recovery Services",
            ordered_by_user=owner,
            notes=(
                "Second missed payment. Recovery agent dispatched "
                "per FDCPA cooling-off window."
            ),
        )

    stdout.write(
        "extended BHPH portfolio: current + delinquent + in-repossession."
    )
    return {
        "current": archetype_note.pk if archetype_note else None,
        "delinquent": delinquent_note.pk if delinquent_note else None,
        "in_repossession": repo_note.pk if repo_note else None,
    }


def _originate_bhph_sale_and_note(
    *,
    dealership: Dealership,
    stock: str,
    buyer_name: str,
    buyer_email: str,
    buyer_phone: str,
    days_ago_sold: int,
    first_payment_days_ago: int,
) -> BhphNote | None:
    """Origination helper: create a lead → BHPH sale → BHPH note.

    Uses model-direct writes for the Sale (rather than
    ``record_sale``) because ``record_sale`` fires the M15 sibling
    GL post which requires a fully-configured VehicleCost history —
    the archetype already provisioned that for its 5 canonical
    sales, but ad-hoc extension sales here need not carry the same
    coherence contract; the demo's trial balance is populated
    elsewhere (see ``_seed_journal_month``).
    """
    now = timezone.now()
    try:
        vehicle = Vehicle.objects.get(
            dealership=dealership, stock_number=stock
        )
    except Vehicle.DoesNotExist:
        return None
    if Sale.objects.filter(vehicle=vehicle).exists():
        return None  # archetype already sold this one; caller mis-configured

    # Buyer as a walk-in lead so the sale has a real customer trail.
    buyer = CustomerLead.objects.create(
        dealership=dealership,
        name=buyer_name,
        email=buyer_email,
        phone=buyer_phone,
        urgency="immediate",
        channel="walk_in",
        created_at=now - dt.timedelta(days=days_ago_sold + 1),
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        buyer=buyer,
        sale_date=(now - dt.timedelta(days=days_ago_sold)).date(),
        sold_price=vehicle.price,
        finance_type=SALE_FINANCE_TYPE_BHPH,
        lender_name="",
        gross_realized=Decimal("0.00"),
    )

    # Mirror the ``record_sale`` side effects by hand — this helper
    # writes the Sale directly (see class docstring) so the sale-hook
    # transitions must be re-composed here. Otherwise the extension's
    # sold BHPH units would sit on frontline and read as available
    # stock forever.
    stage = get_current_stage(vehicle, dealership=dealership)
    if stage is not None and stage.current_stage == VEHICLE_STAGE_FRONTLINE:
        advance_stage(
            vehicle,
            dealership=dealership,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
            trigger=VEHICLE_STAGE_TRIGGER_RULE,
            rule_name="sale_booked",
            notes=f"Sale #{sale.pk} booked (extension seed).",
        )
    if vehicle.is_available:
        vehicle.is_available = False
        vehicle.save(update_fields=["is_available"])

    first_payment_due = (
        now - dt.timedelta(days=first_payment_days_ago)
    ).date()
    note = record_bhph_note(
        dealership=dealership,
        sale=sale,
        principal_financed=vehicle.price,
        apr=Decimal("18.9"),
        term_weeks=104,  # 24 months / ~2 years
        payment_frequency="weekly",
        first_payment_due=first_payment_due,
    )
    return note


# ---------------------------------------------------------------------------
# F&I chain — DealStructures, LenderSubmissions, Contract, Stipulation
# ---------------------------------------------------------------------------


def _extend_fni_chain(dealership: Dealership, owner, stdout) -> dict:
    """Build the F&I chain on the archetype's 2 credit apps + add a
    third bare CA so both /dealer-ai-f-and-i and
    /dealer-ai-f-and-i/incoming show non-trivial content.

    Layout after this runs:
    - CA-A (RS-15 sale): DealStructure + LenderSubmission (approved)
      + Contract (signed) + Funding (pending). Appears in
      /admin/f-and-i/deals/. NOT in intake (has Contract).
    - CA-B (RS-16 sale): DealStructure + LenderSubmission (pending)
      + open Stipulation (proof of income). Still in intake.
    - CA-C (fresh, no DealStructure): a bare intake row so the
      queue shows the "Incoming" chip alongside the "Structure
      started" chip on CA-B.
    """
    # Lender program the demo can reference from both CAs.
    # The Copper Canyon persona (docs/research/INDEPENDENT_DEALER_
    # PIVOT.md) names three subprime partners plus in-house BHPH.
    # Seed all three; the CA-A path submits to the primary
    # subprime partner. The extras give the F&I list screen a
    # realistic lender roster to browse instead of a single row.
    lender = record_lender_program(
        dealership=dealership,
        name="Sonoran Auto Finance",
        contact="Loan officer: Rafael Cardenas",
        terms_summary="48-72 mo, 580+ FICO, subprime specialist.",
        is_active=True,
    )
    record_lender_program(
        dealership=dealership,
        name="Border Credit Partners",
        contact="Loan officer: Jasmine Wu",
        terms_summary="60-84 mo, 600+ FICO, thin-file friendly.",
        is_active=True,
    )
    record_lender_program(
        dealership=dealership,
        name="Colorado Basin Federal Credit Union",
        contact="Loan officer: Diego Alarcon",
        terms_summary=(
            "60-72 mo, 640+ FICO, community-CU rates for members."
        ),
        is_active=True,
    )

    apps_by_stock: dict[str, CreditApplication] = {}
    for ca in CreditApplication.objects.filter(dealership=dealership):
        if ca.sale is not None and ca.sale.vehicle is not None:
            apps_by_stock[ca.sale.vehicle.stock_number] = ca

    signed_contract_pk = None
    stipulation_pk = None
    bare_ca_pk = None

    # ---- Path A: CA-A → DealStructure → Approved submission →
    # Signed contract → Pending funding.
    ca_a = apps_by_stock.get("RS-15")
    if ca_a is not None:
        vehicle_a = ca_a.sale.vehicle
        deal_a = record_deal_structure(
            dealership=dealership,
            credit_application=ca_a,
            vehicle=vehicle_a,
            sale_price=Decimal("8995.00"),
            amount_financed=Decimal("7495.00"),
            apr=Decimal("14.9"),
            term_months=48,
            monthly_payment=Decimal("208.00"),
            down_payment=Decimal("1000.00"),
            taxes=Decimal("540.00"),
            fees=Decimal("225.00"),
        )
        record_lender_submission(
            dealership=dealership,
            deal_structure=deal_a,
            lender_program=lender,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
            approval_terms={
                "apr_pct": "14.9",
                "term_months": 48,
                "amount_financed": "7495.00",
                "reserve_amount": "325.00",
                "conditions": "Proof of insurance at delivery.",
            },
        )
        contract_a = record_contract(
            dealership=dealership,
            deal_structure=deal_a,
            contract_type=CONTRACT_TYPE_RISC,
            signer_name="Angela Reyes",
            financed_amount=Decimal("7495.00"),
            total_of_payments=Decimal("9984.00"),
            finance_charge=Decimal("2489.00"),
            apr_disclosure=Decimal("14.9000"),
            first_payment_date=(
                timezone.now().date() + dt.timedelta(days=30)
            ),
        )
        sign_contract(
            contract_a,
            signer_name="Angela Reyes",
            signed_at=timezone.now() - dt.timedelta(days=2),
        )
        record_funding(
            dealership=dealership,
            contract=contract_a,
            submitted_to_lender_at=timezone.now() - dt.timedelta(days=1),
            notes="Funding packet submitted; awaiting lender wire.",
        )
        signed_contract_pk = contract_a.pk

    # ---- Path B: CA-B → DealStructure → Pending submission → open Stip.
    ca_b = apps_by_stock.get("RS-16")
    if ca_b is not None:
        vehicle_b = ca_b.sale.vehicle
        deal_b = record_deal_structure(
            dealership=dealership,
            credit_application=ca_b,
            vehicle=vehicle_b,
            sale_price=Decimal("9495.00"),
            amount_financed=Decimal("8495.00"),
            apr=Decimal("17.9"),
            term_months=60,
            monthly_payment=Decimal("215.00"),
            down_payment=Decimal("500.00"),
            taxes=Decimal("570.00"),
            fees=Decimal("225.00"),
        )
        submission_b = record_lender_submission(
            dealership=dealership,
            deal_structure=deal_b,
            lender_program=lender,
            status=LENDER_SUBMISSION_STATUS_PENDING,
        )
        stip = record_stipulation(
            dealership=dealership,
            lender_submission=submission_b,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
            notes=(
                "Lender wants two most recent pay stubs plus a W-2 "
                "before final approval."
            ),
        )
        stipulation_pk = stip.pk

    # ---- Path C: fresh CA against an unsold frontline lead, no
    # DealStructure. Intake queue still shows an "Incoming" row.
    lead_c = (
        CustomerLead.objects.filter(dealership=dealership)
        .order_by("pk")
        .first()
    )
    if lead_c is not None:
        ca_c = record_credit_application(
            dealership=dealership,
            applicant_full_name="Nathan Wei",
            source_format=CREDIT_APP_FORMAT_TABLET,
            lead=lead_c,
            captured_at=timezone.now() - dt.timedelta(hours=6),
            notes=(
                "Sales manager captured on the tablet during walk-in. "
                "No structure yet — needs vehicle match."
            ),
        )
        bare_ca_pk = ca_c.pk

    stdout.write(
        f"F&I chain built: contract={signed_contract_pk} "
        f"stipulation={stipulation_pk} bare_intake_ca={bare_ca_pk}."
    )
    return {
        "signed_contract_pk": signed_contract_pk,
        "stipulation_pk": stipulation_pk,
        "bare_intake_ca_pk": bare_ca_pk,
    }


# ---------------------------------------------------------------------------
# Sales-side channels — test drives + one be-back due today
# ---------------------------------------------------------------------------


def _seed_test_drives(dealership: Dealership, stdout) -> int:
    """Schedule 2 test drives against archetype leads + vehicles.

    Picks the first two assigned leads and their interested-vehicle
    mapping from the archetype. Backdates one recent (yesterday);
    schedules one for later today so the operator's "today's
    activity" card has something upcoming.
    """
    now = timezone.now()
    leads = list(
        CustomerLead.objects.filter(
            dealership=dealership, assigned_to__isnull=False
        ).order_by("pk")[:2]
    )
    if not leads:
        stdout.write("no assigned leads found; skipping test drives.")
        return 0

    # Pair with the first two unsold vehicles (any stage that
    # isn't off-market). By the time this runs, BHPH extension has
    # sold two frontline vehicles and the archetype sold five, so
    # scoping to `stage=frontline` alone can come up empty; a test
    # drive against any unsold vehicle reads fine on the demo.
    candidate_vehicles = list(
        Vehicle.objects.filter(
            dealership=dealership,
            sale__isnull=True,
        )
        .exclude(stage__current_stage=VEHICLE_STAGE_OFF_MARKET)
        .exclude(stage__current_stage=VEHICLE_STAGE_WHOLESALE_OUT)
        .order_by("pk")[:2]
    )
    seeded = 0
    for offset, (lead, vehicle) in enumerate(
        zip(leads, candidate_vehicles)
    ):
        driven_at = (
            now - dt.timedelta(days=1) if offset == 0
            else now + dt.timedelta(hours=3)
        )
        record_test_drive(
            dealership=dealership,
            lead=lead,
            vehicle=vehicle,
            driven_at=driven_at,
            duration_minutes=30 if offset == 0 else None,
            route_notes=(
                "Standard 8-mile loop — highway on Frontage Road, "
                "brake test on the descent."
                if offset == 0
                else "Scheduled — customer arriving after lunch."
            ),
            customer_reaction=(
                "Liked the ride quality, wants to bring their "
                "spouse back tomorrow."
                if offset == 0
                else ""
            ),
        )
        seeded += 1
    stdout.write(f"seeded {seeded} test drive(s).")
    return seeded


def _seed_be_back(dealership: Dealership, stdout):
    """Create one be-back due today so the sales-side "today" card
    reads real. Reuses one of the archetype's assigned leads.
    """
    now = timezone.now()
    lead = (
        CustomerLead.objects.filter(
            dealership=dealership, assigned_to__isnull=False
        )
        .order_by("-pk")
        .first()
    )
    if lead is None:
        stdout.write("no assigned lead for be-back; skipping.")
        return None
    # Promised for later today; slightly in the past shows the
    # "overdue today" chip if the operator opens the page late.
    promised_at = now.replace(hour=17, minute=0, second=0, microsecond=0)
    be_back = record_be_back(
        dealership=dealership,
        lead=lead,
        promised_at=promised_at,
        promised_reason=BE_BACK_REASON_TEST_DRIVE,
        notes=(
            "Customer promised to return this afternoon with their "
            "spouse for a second test drive."
        ),
    )
    stdout.write(
        f"seeded be-back pk={be_back.pk} due {promised_at.isoformat()}."
    )
    return be_back


# ---------------------------------------------------------------------------
# Journal entries — a month of realistic operational entries
# ---------------------------------------------------------------------------


# (offset days ago, description, debit_code, credit_code, amount)
_JOURNAL_ENTRIES: tuple[tuple[int, str, str, str, str], ...] = (
    (30, "Monthly rent — Yuma showroom + lot", "800000", "110000", "4800.00"),
    (29, "Google Ads — March campaign accrual", "600000", "200000", "620.00"),
    (28, "Facebook Ads — March campaign accrual", "600000", "200000", "380.00"),
    (27, "Sales salaries — March run 1", "700000", "110000", "5400.00"),
    (25, "Cash deposit from used vehicle sale RS-12", "110000", "100000", "10495.00"),
    (24, "Owner draw — March 15", "300000", "110000", "2000.00"),
    (22, "Floor plan interest accrual — Feb close", "900000", "210000", "1250.00"),
    (20, "Vendor payable — Desert Auto Repair Feb invoice", "510000", "200000", "1420.00"),
    (17, "Sales salaries — March run 2", "700000", "110000", "5400.00"),
    (15, "Detail supplies + shop consumables", "510000", "200000", "295.00"),
    (12, "Cash deposit from retail sale RS-15", "110000", "100000", "8995.00"),
    (10, "Customer deposit received — hold RS-16", "110000", "230000", "500.00"),
    (8, "Advertising — local radio spot", "600000", "110000", "450.00"),
    (5, "Vendor payment — Desert Auto Repair Feb clear", "200000", "110000", "1420.00"),
    (2, "Sales salaries — April run 1", "700000", "110000", "5400.00"),
)


def _seed_journal_month(
    dealership: Dealership, owner, stdout
) -> int:
    """Post ~15 miscellaneous journal entries spread over 30 days.

    The archetype's ``record_sale`` calls post their own sale-booking
    JEs, so the trial balance is not empty after the archetype
    build. This layer adds the operational-noise entries a
    bookkeeper would recognize: rent, payroll, ads, floor plan
    interest, vendor payables, cash deposits.

    Composes ``services.accounting.journal.post_journal_entry`` —
    every entry balanced (debits == credits), against the default
    COA codes seeded by ``seed_default_coa``.
    """
    now = timezone.now()
    accounts_by_code: dict[str, GLAccount] = {
        acc.code: acc
        for acc in GLAccount.objects.filter(dealership=dealership)
    }

    posted = 0
    for days_ago, description, debit_code, credit_code, amount_str in (
        _JOURNAL_ENTRIES
    ):
        debit_acc = accounts_by_code.get(debit_code)
        credit_acc = accounts_by_code.get(credit_code)
        if debit_acc is None or credit_acc is None:
            stdout.write(
                f"  skip JE {description!r}: missing GL account "
                f"debit={debit_code} credit={credit_code}."
            )
            continue
        amount = Decimal(amount_str)
        post_journal_entry(
            dealership=dealership,
            description=description,
            lines=[
                JournalLineInput(account=debit_acc, debit=amount, memo=""),
                JournalLineInput(account=credit_acc, credit=amount, memo=""),
            ],
            posted_at=now - dt.timedelta(days=days_ago, hours=1),
            posted_by_user=owner,
        )
        posted += 1
    stdout.write(
        f"posted {posted} manual journal entries across 30 days."
    )
    return posted


# ---------------------------------------------------------------------------
# Chat sessions + guard events — the audit panel + coaching mode
# ---------------------------------------------------------------------------


# One shape per chat session. ``flag`` populates ChatMessage.metadata
# and drives the audit-events endpoint's category totals (see
# ``services/audit.py:33`` for the flag → category map). Chosen flags
# span the four categories a guard-events panel is meant to expose:
# a pre-LLM short-circuit, a post-LLM rewrite, and a scrub.
_CHAT_SCENARIOS: tuple[dict, ...] = (
    {
        "customer_name": "Jorge Ramirez",
        "customer_phone": "(928) 555-0138",
        "minutes_ago": 30,
        "extracted_profile": {
            "intent": "vehicle_search",
            "vehicle_type": "truck",
            "credit_range": "unknown",
            "urgency": "this_week",
        },
        "user_message": (
            "Hi — I'm looking for a used truck under $12k. Interested in "
            "the Ranger you have listed."
        ),
        "assistant_message": (
            "Great — the 2015 Ford Ranger XLT at $11,795 is the closest "
            "match. Want me to have a sales advisor confirm it's on the "
            "lot and set up a time to see it?"
        ),
        "assistant_flag": None,  # clean session, no guard event
    },
    {
        "customer_name": "Alicia Perez",
        "customer_phone": "(928) 555-0142",
        "minutes_ago": 90,
        "extracted_profile": {
            "intent": "rate_inquiry",
            "urgency": "immediate",
        },
        "user_message": "What APR would you give me on the Corolla?",
        "assistant_message": (
            "APR depends on your credit and lender — I can't quote a rate "
            "myself, but an advisor can run real numbers with you. Want me "
            "to connect you?"
        ),
        # rate_inquiry → pre_llm_guard category (see services/audit.py)
        "assistant_flag": "rate_inquiry",
    },
    {
        "customer_name": "Devon Wallace",
        "customer_phone": "(928) 555-0155",
        "minutes_ago": 180,
        "extracted_profile": {
            "intent": "negotiation_request",
            "vehicle_type": "sedan",
        },
        "user_message": (
            "Can you knock $2000 off the sticker on the Fusion? I saw "
            "one cheaper across town."
        ),
        "assistant_message": (
            "Pricing negotiations are handled by a sales advisor — I can "
            "note your offer and hand you off. Want me to do that?"
        ),
        # negotiation_request → pre_llm_guard
        "assistant_flag": "negotiation_request",
    },
    {
        "customer_name": "Priya Nair",
        "customer_phone": "(928) 555-0169",
        "minutes_ago": 340,
        "extracted_profile": {
            "intent": "vehicle_search",
            "vehicle_type": "suv",
        },
        "user_message": (
            "Do you have anything with third-row seating under $15k?"
        ),
        "assistant_message": (
            "Let me check current inventory — I want to be careful not to "
            "invent a vehicle we don't have. An advisor can confirm what "
            "just landed."
        ),
        # fabricated_inventory → post_llm_rewrite
        "assistant_flag": "fabricated_inventory",
    },
)


def _seed_chat_sessions_with_guard_events(
    dealership: Dealership, stdout
) -> dict:
    """Seed four ChatSession + ChatMessage pairs so /admin/chat-sessions/
    and /admin/audit-events/ return non-empty payloads.

    Three of the four assistant messages carry a ``flag`` in
    ``metadata``, matching the shape expected by
    ``services/audit.py:audit_events_snapshot`` (see
    ``_FLAG_CATEGORIES``). Flags span three categories so the guard-
    events panel exposes non-zero totals across pre-LLM guards and
    post-LLM rewrites.
    """
    now = timezone.now()
    session_count = 0
    guard_events = 0
    for scenario in _CHAT_SCENARIOS:
        session = ChatSession.objects.create(
            dealership=dealership,
            customer_name=scenario["customer_name"],
            customer_phone=scenario["customer_phone"],
            extracted_profile=scenario["extracted_profile"],
            metadata={"demo_tag": "copper_canyon_auto_demo"},
        )
        # Backdate created_at so the "recent activity" panel spreads
        # across the day rather than clustering at seed time.
        anchor = now - dt.timedelta(minutes=scenario["minutes_ago"])
        ChatSession.objects.filter(pk=session.pk).update(created_at=anchor)

        user_msg = ChatMessage.objects.create(
            dealership=dealership,
            session=session,
            role="user",
            content=scenario["user_message"],
            metadata={},
        )
        ChatMessage.objects.filter(pk=user_msg.pk).update(created_at=anchor)

        assistant_metadata = {}
        if scenario["assistant_flag"]:
            assistant_metadata = {
                "provider": "guard",
                "flag": scenario["assistant_flag"],
            }
            guard_events += 1
        assistant_msg = ChatMessage.objects.create(
            dealership=dealership,
            session=session,
            role="assistant",
            content=scenario["assistant_message"],
            metadata=assistant_metadata,
        )
        assistant_anchor = anchor + dt.timedelta(seconds=45)
        ChatMessage.objects.filter(pk=assistant_msg.pk).update(
            created_at=assistant_anchor
        )
        session_count += 1
    stdout.write(
        f"seeded {session_count} chat session(s) with "
        f"{guard_events} guard-event message(s)."
    )
    return {"sessions": session_count, "guard_events": guard_events}


# ---------------------------------------------------------------------------
# Stage aging snapshots — 14 days of history so trend endpoints draw
# ---------------------------------------------------------------------------


def _seed_stage_aging_snapshots(
    dealership: Dealership, stdout
) -> int:
    """Backfill ~14 days of :class:`StageAgingSnapshot` rows.

    Composes ``services.lifecycle_aging.snapshots.snapshot_stage_ages``
    (the M7.3 verb the Celery job also calls). Each backfilled
    snapshot reads the *current* ``VehicleStage.entered_at`` values
    and computes days-in-stage relative to the passed ``snapshot_at``
    — so the "trend" is a linear shift of the current state across
    the window rather than a real historical replay. That is enough
    for the ``/admin/analytics/stage-aging-trend/`` and
    ``days-at-frontline-proxy`` endpoints to draw a line instead of
    returning empty.
    """
    now = timezone.now()
    written = 0
    for days_ago in range(14, -1, -1):
        snapshot_at = now - dt.timedelta(days=days_ago)
        result = snapshot_stage_ages(
            dealership, snapshot_at=snapshot_at
        )
        written += result.written_count
    stdout.write(
        f"backfilled {written} stage-aging snapshot row(s) across 14 days."
    )
    return written


# ---------------------------------------------------------------------------
# Lot expansion — bring the store up to Chris's operating-scale rule:
# ~50 for-sale + ~25-30 in prep + ~40 sold in the trailing month.
#
# The archetype hardcodes 20 vehicles at ``retail_subprime.py:363`` and
# `services/demo_store/` is out of bounds. The expansion synthesises
# 72 additional used-vehicle rows and lands them through the shipped
# :func:`services.inventory_import.import_rows` verb — the same path a
# real dealer's CSV feed uses. That keeps the seed composing existing
# verbs instead of hand-writing Vehicle rows, and it exercises the
# import contract as a side effect.
#
# See docs/_internal/TASK_c2c3-lot-shape-and-demo-script.md — "Row
# projection for the resize" for the derivation.
# ---------------------------------------------------------------------------


# Mixed-make used inventory templates the extension picks from. Prices
# span the archetype's $8-18k band; makes/models match the Yuma indie
# persona (Ford / Chevy / Toyota / Honda / Nissan / Hyundai / Kia).
# Body-style mix reflects a lot serving working families + snowbirds:
# trucks, SUVs, sedans and one van.
_EXPANSION_VEHICLE_TEMPLATES: tuple[dict, ...] = (
    {"make": "Ford", "model": "F-150", "trim": "XLT SuperCab", "body_style": "truck", "price_base": 15495, "mileage_base": 118000},
    {"make": "Ford", "model": "F-150", "trim": "STX Regular Cab", "body_style": "truck", "price_base": 12995, "mileage_base": 135000},
    {"make": "Ford", "model": "Escape", "trim": "SE", "body_style": "suv", "price_base": 12295, "mileage_base": 112000},
    {"make": "Ford", "model": "Focus", "trim": "SE Hatch", "body_style": "car", "price_base": 8495, "mileage_base": 128000},
    {"make": "Ford", "model": "Fusion", "trim": "SE", "body_style": "car", "price_base": 9995, "mileage_base": 122000},
    {"make": "Ford", "model": "Explorer", "trim": "XLT 4WD", "body_style": "suv", "price_base": 14795, "mileage_base": 129000},
    {"make": "Ford", "model": "Ranger", "trim": "XLT Extended Cab", "body_style": "truck", "price_base": 10995, "mileage_base": 145000},
    {"make": "Chevrolet", "model": "Silverado 1500", "trim": "LT", "body_style": "truck", "price_base": 16995, "mileage_base": 115000},
    {"make": "Chevrolet", "model": "Silverado 1500", "trim": "WT Regular Cab", "body_style": "truck", "price_base": 12995, "mileage_base": 138000},
    {"make": "Chevrolet", "model": "Equinox", "trim": "LT AWD", "body_style": "suv", "price_base": 13295, "mileage_base": 108000},
    {"make": "Chevrolet", "model": "Traverse", "trim": "LT", "body_style": "suv", "price_base": 15795, "mileage_base": 121000},
    {"make": "Chevrolet", "model": "Malibu", "trim": "LT", "body_style": "car", "price_base": 10495, "mileage_base": 118000},
    {"make": "Chevrolet", "model": "Colorado", "trim": "Z71 Crew Cab", "body_style": "truck", "price_base": 17495, "mileage_base": 102000},
    {"make": "Toyota", "model": "Tacoma", "trim": "SR5 Access Cab", "body_style": "truck", "price_base": 17995, "mileage_base": 116000},
    {"make": "Toyota", "model": "Tacoma", "trim": "TRD Off-Road Double Cab", "body_style": "truck", "price_base": 21495, "mileage_base": 108000},
    {"make": "Toyota", "model": "Tundra", "trim": "SR5 Double Cab", "body_style": "truck", "price_base": 19995, "mileage_base": 122000},
    {"make": "Toyota", "model": "RAV4", "trim": "LE AWD", "body_style": "suv", "price_base": 13795, "mileage_base": 115000},
    {"make": "Toyota", "model": "Highlander", "trim": "LE V6", "body_style": "suv", "price_base": 16295, "mileage_base": 125000},
    {"make": "Toyota", "model": "Camry", "trim": "LE", "body_style": "car", "price_base": 11495, "mileage_base": 128000},
    {"make": "Toyota", "model": "Corolla", "trim": "LE", "body_style": "car", "price_base": 10795, "mileage_base": 118000},
    {"make": "Toyota", "model": "Sienna", "trim": "LE 8-Passenger", "body_style": "van", "price_base": 14995, "mileage_base": 132000},
    {"make": "Honda", "model": "CR-V", "trim": "EX-L", "body_style": "suv", "price_base": 15295, "mileage_base": 112000},
    {"make": "Honda", "model": "Pilot", "trim": "EX-L", "body_style": "suv", "price_base": 16795, "mileage_base": 128000},
    {"make": "Honda", "model": "Civic", "trim": "EX", "body_style": "car", "price_base": 11995, "mileage_base": 118000},
    {"make": "Honda", "model": "Accord", "trim": "Sport", "body_style": "car", "price_base": 12495, "mileage_base": 121000},
    {"make": "Honda", "model": "Ridgeline", "trim": "RTL", "body_style": "truck", "price_base": 18995, "mileage_base": 116000},
    {"make": "Nissan", "model": "Rogue", "trim": "SV", "body_style": "suv", "price_base": 11795, "mileage_base": 123000},
    {"make": "Nissan", "model": "Altima", "trim": "2.5 SV", "body_style": "car", "price_base": 10495, "mileage_base": 130000},
    {"make": "Nissan", "model": "Frontier", "trim": "SV Crew Cab", "body_style": "truck", "price_base": 13795, "mileage_base": 128000},
    {"make": "Nissan", "model": "Sentra", "trim": "SV", "body_style": "car", "price_base": 8995, "mileage_base": 132000},
    {"make": "Hyundai", "model": "Elantra", "trim": "SE", "body_style": "car", "price_base": 8495, "mileage_base": 126000},
    {"make": "Hyundai", "model": "Sonata", "trim": "SE", "body_style": "car", "price_base": 9795, "mileage_base": 118000},
    {"make": "Hyundai", "model": "Santa Fe", "trim": "Sport", "body_style": "suv", "price_base": 12495, "mileage_base": 122000},
    {"make": "Kia", "model": "Sorento", "trim": "LX V6", "body_style": "suv", "price_base": 11995, "mileage_base": 124000},
    {"make": "Kia", "model": "Optima", "trim": "LX", "body_style": "car", "price_base": 9295, "mileage_base": 128000},
    {"make": "Kia", "model": "Forte", "trim": "S", "body_style": "car", "price_base": 8195, "mileage_base": 121000},
)


# Stage targets AFTER expansion — the shape a 50-car indie lot should
# read as. Delta rows above the archetype baseline (which the existing
# ``_STAGE_PLAN`` establishes for the 20 archetype vehicles) are
# distributed here from the freshly-imported CC-#### stock. Frontline
# is the residual — every imported vehicle not moved to another stage
# stays there.
_STAGE_EXPANSION_TARGETS: tuple[tuple[str, int], ...] = (
    (VEHICLE_STAGE_INCOMING, 3),
    (VEHICLE_STAGE_INSPECTION, 5),
    (VEHICLE_STAGE_RECON, 9),
    (VEHICLE_STAGE_DETAIL, 3),
    (VEHICLE_STAGE_PHOTOGRAPHY, 2),
    (VEHICLE_STAGE_QC, 4),
    (VEHICLE_STAGE_LISTING, 2),
    (VEHICLE_STAGE_COMPANY_USE, 2),
    (VEHICLE_STAGE_WHOLESALE_OUT, 2),
)

# Days-ago patterns for entered_at on the redistributed CC-#### stock.
# Vehicles that just landed should read fresh (small days-ago); ones
# further into recon or listing should read like they have been there
# a bit. Applied via modulus so 10 vehicles in a stage cycle through
# the days list.
_STAGE_EXPANSION_DAYS_AGO: dict[str, tuple[int, ...]] = {
    VEHICLE_STAGE_INCOMING: (1, 2, 3),
    VEHICLE_STAGE_INSPECTION: (2, 4, 5),
    VEHICLE_STAGE_RECON: (3, 6, 9, 12, 15),
    VEHICLE_STAGE_DETAIL: (4, 6, 8),
    VEHICLE_STAGE_PHOTOGRAPHY: (5, 8),
    VEHICLE_STAGE_QC: (5, 7, 9, 11),
    VEHICLE_STAGE_LISTING: (10, 14),
    VEHICLE_STAGE_COMPANY_USE: (60, 120),
    VEHICLE_STAGE_WHOLESALE_OUT: (30, 55),
}


# Total unsold vehicles the expansion should land immediately after
# import — the number that later shrinks as extensions sell some off.
# The math: we want ~85 unsold at end-of-seed. Extension pipeline
# sells 40 more vehicles after import (2 in ``_extend_bhph_portfolio``
# + 38 in ``_extend_sales_history``). So import time needs 85 + 40 =
# 125 unsold on the lot, minus whatever the archetype already left
# unsold (15). Net new imports: ~110. Adjust the final target if the
# extension sales count changes.
_EXPANSION_TARGET_UNSOLD_COUNT: int = 125


def _synthesise_expansion_rows(
    count: int, start_stock_index: int = 1
) -> list[tuple[int, dict]]:
    """Build ``count`` vehicle rows drawn from
    :data:`_EXPANSION_VEHICLE_TEMPLATES`.

    Deterministic — the same ``count`` produces the same rows every
    run (indexes into the template list mod its length). Year, price
    and mileage are stepped off the template's base so no two
    generated vehicles are identical, but the base ratios (Toyota
    truck holds its money, Kia sedan does not) stay realistic.

    Returns a list shaped for :func:`import_rows`:
    ``[(line_no, row_dict), ...]``. ``line_no`` is a synthetic 1-based
    row index — the import service uses it only for error reporting.
    """
    templates = _EXPANSION_VEHICLE_TEMPLATES
    now_year = timezone.now().year
    rows: list[tuple[int, dict]] = []
    for i in range(count):
        tpl = templates[i % len(templates)]
        # Year rotates 2010-2020 so the lot reads mixed-age.
        year = 2010 + ((i * 3 + 1) % 11)
        # Price varies ±10 % around the base so no two vehicles at
        # the same template land at the same sticker.
        price_delta = -800 + (i * 173 % 1600)
        price = tpl["price_base"] + price_delta
        # Mileage varies ±15 % around the base.
        mileage_delta = -12000 + (i * 2711 % 24000)
        mileage = max(45_000, tpl["mileage_base"] + mileage_delta)
        stock = f"CC-{start_stock_index + i:03d}"
        vin = f"CCA{i:03d}{tpl['make'][0]}{tpl['model'][0]}{year}XXXXX"[:17].ljust(
            17, "0"
        )
        rows.append(
            (
                i + 1,
                {
                    "stock_number": stock,
                    "vin": vin,
                    "year": year,
                    "make": tpl["make"],
                    "model": tpl["model"],
                    "trim": tpl["trim"],
                    "condition": "used",
                    "price": str(price),
                    "mileage": str(mileage),
                    "body_style": tpl["body_style"],
                    "fuel_type": "Gasoline",
                    "url": "",
                    "image_url": "",
                    "features": "",
                },
            )
        )
    return rows


def _extend_lot_to_target_size(
    dealership: Dealership, stdout
) -> int:
    """Bring the store's unsold pool up to
    :data:`_EXPANSION_TARGET_UNSOLD_COUNT` by synthesising rows and
    feeding them through the shipped inventory-import verb.

    ``mark_missing_unavailable=False`` — the default flips every row
    *not* present in the batch to ``is_available=False``, which
    would silently mark the archetype's 20 originals unavailable
    the first time this ran. Cowork's review flagged the trap; we
    pass ``False`` and let the archetype rows stand.

    Every imported vehicle also gets a :class:`VehicleAcquisition`
    row so :func:`services.sale.record_sale` can compute a truthful
    ``gross_realized`` at sale time. Purchase price runs ~60 % of
    retail — the ratio the archetype uses for its ``cost_basis``.

    Returns the number of vehicles created.
    """
    now = timezone.now()
    unsold_current = (
        Vehicle.objects.filter(dealership=dealership, sale__isnull=True).count()
    )
    to_add = max(0, _EXPANSION_TARGET_UNSOLD_COUNT - unsold_current)
    if to_add == 0:
        stdout.write(
            "lot already at or over the expansion target — nothing to add."
        )
        return 0

    rows = _synthesise_expansion_rows(to_add)
    summary = import_rows(
        rows,
        source="copper_canyon_seed",
        dry_run=False,
        mark_missing_unavailable=False,
        dealership=dealership,
    )

    # Provision VehicleAcquisition for each newly-imported vehicle so
    # ``record_sale`` can compute a truthful ``gross_realized`` at
    # sale time. Purchase price = 60 % of retail (matches the
    # archetype's ``cost_basis`` ratio). Skip vehicles that somehow
    # already have an acquisition (idempotent re-runs of this
    # function against a partial state).
    provisioned = 0
    for offset, stock in enumerate(summary.seen_stock_numbers):
        try:
            vehicle = Vehicle.objects.get(
                dealership=dealership, stock_number=stock
            )
        except Vehicle.DoesNotExist:  # pragma: no cover — defensive
            continue
        if VehicleAcquisition.objects.filter(vehicle=vehicle).exists():
            continue
        # Deterministic source mix mirroring the archetype (auction /
        # trade / private in a 1:1:1 rotation).
        source = (
            SOURCE_AUCTION if offset % 3 == 0
            else SOURCE_TRADE if offset % 3 == 1
            else SOURCE_PRIVATE
        )
        purchase_price = (vehicle.price * Decimal("0.6")).quantize(
            Decimal("1.00")
        )
        # Purchase date runs 30-90 days ago so acquisitions predate
        # every sale the seed lands afterward.
        days_ago = 30 + (offset * 7) % 61
        VehicleAcquisition.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            source=source,
            purchase_price=purchase_price,
            purchase_date=(now - dt.timedelta(days=days_ago)).date(),
            source_detail=f"{source[:3].upper()}-CC{offset:03d}",
        )
        provisioned += 1

    stdout.write(
        f"extended lot: imported {summary.created} vehicle(s) "
        f"(updated={summary.updated}, invalid={len(summary.invalid_rows)}), "
        f"provisioned {provisioned} acquisition row(s). "
        f"Unsold pool: {unsold_current} → "
        f"{unsold_current + summary.created}."
    )
    return summary.created


def _expand_stage_distribution(
    dealership: Dealership, stdout
) -> None:
    """Redistribute freshly-imported ``CC-####`` frontline vehicles
    into the prep and holdover stages until each hits its
    :data:`_STAGE_EXPANSION_TARGETS` count.

    Only touches ``CC-####`` stock — archetype rows (``RS-##``)
    keep whatever :func:`_distribute_lifecycle_stages` already
    assigned them. Frontline is the residual: everything not moved
    stays there, which lands ~50 vehicles for sale.

    Each stage move rewrites :class:`VehicleStage` +
    :class:`VehicleStageEvent` directly (matching the pattern in
    :func:`_distribute_lifecycle_stages`) — bypassing
    :func:`advance_stage`'s transition table so ``frontline →
    photography`` and other short-hop moves don't need a table
    edit for a seed-only side path.
    """
    now = timezone.now()
    reassigned = 0
    for stage_key, target_count in _STAGE_EXPANSION_TARGETS:
        current = VehicleStage.objects.filter(
            dealership=dealership, current_stage=stage_key
        ).count()
        need = max(0, target_count - current)
        if need == 0:
            continue
        days_pattern = _STAGE_EXPANSION_DAYS_AGO.get(stage_key, (5,))
        # Pull CC-#### frontline vehicles in stock-number order so
        # the assignment is deterministic across re-runs.
        candidates = list(
            VehicleStage.objects.filter(
                dealership=dealership,
                current_stage=VEHICLE_STAGE_FRONTLINE,
                vehicle__stock_number__startswith="CC-",
            )
            .select_related("vehicle")
            .order_by("vehicle__stock_number")[:need]
        )
        for offset, stage_row in enumerate(candidates):
            days_ago = days_pattern[offset % len(days_pattern)]
            entered_at = now - dt.timedelta(days=days_ago)
            previous_stage = stage_row.current_stage
            stage_row.current_stage = stage_key
            stage_row.entered_at = entered_at
            stage_row.trigger = VEHICLE_STAGE_TRIGGER_MANUAL
            stage_row.save(
                update_fields=[
                    "current_stage", "entered_at", "trigger",
                ]
            )
            # Backdate whichever earlier event still sits after the
            # new manual transition — the log-not-backwards invariant
            # :func:`_distribute_lifecycle_stages` also protects.
            # Prod imports create a ``trigger='import'`` event; the
            # test-only auto-bootstrap post_save signal
            # (dealer_ai/tests/__init__.py) writes ``trigger='bootstrap'``.
            # Filter both so the log stays chronological in either env.
            VehicleStageEvent.objects.filter(
                vehicle=stage_row.vehicle,
                trigger__in=("import", "bootstrap"),
                entered_at__gt=entered_at,
            ).update(
                entered_at=entered_at - dt.timedelta(hours=1),
            )
            VehicleStageEvent.objects.create(
                dealership=dealership,
                vehicle=stage_row.vehicle,
                from_stage=previous_stage,
                to_stage=stage_key,
                entered_at=entered_at,
                trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
                notes="Copper Canyon demo seed — stage expansion.",
            )
            reassigned += 1
    stdout.write(
        f"expanded stage distribution: reassigned {reassigned} "
        f"CC-#### vehicle(s) across "
        f"{len(_STAGE_EXPANSION_TARGETS)} target stages."
    )


# Sales-history expansion — 38 more sales in the trailing month so the
# store reads as a working lot at Chris's pace. Mix per the pivot doc:
# subprime-first (20 % cash · 45 % retail · 35 % BHPH).
_EXTENDED_SALES_TOTAL = 38
_EXTENDED_SALES_CASH = 8   # 20 %
_EXTENDED_SALES_RETAIL = 17  # 45 %
_EXTENDED_SALES_BHPH = 13   # 35 %


# ---------------------------------------------------------------------------
# Deliberate losers — TASK_losing-deals-and-the-inventory-page (2026-09-01).
#
# Not every retail sale makes money. A dealer with a truthful demo needs
# a few losing sales in the trailing month so the analytics chain
# (aggregate gross, gross-profit trend crossing zero, mean_gross_pct
# rendering negative, trial balance still balancing) has been exercised
# with signed values — not just the archetype's five plus-only sales.
#
# Six of the forty-five sales lose money — roughly one in seven, which
# matches the ratio Chris named on 2026-09-01. Each loser has a
# recognisable business reason a dealer would name looking at the row:
# an aged unit that finally got cut, a recon overrun the shop opened
# up, a trade overallowance to close a deal, two wholesale disposals
# to auction, and a small last-mile price concession the sales
# manager approved.
#
# The stocks (CC-041, CC-047, CC-053, CC-055, CC-058, CC-060) sit
# inside the CC-023..CC-060 range that :func:`_extend_sales_history`
# actually sells (measured 2026-09-01: the archetype's 20 vehicles
# leave 22 of the imported CC-#### stock in prep after
# :func:`_expand_stage_distribution` runs, so the extension pulls
# from CC-023 onward).
#
# The single-loss ceiling :data:`_MAX_LOSER_LOSS` is the read that
# separates a deliberate business decision from a ledger bug. A
# $12,000 loss on a $9,000 car is the archetype's acquisition-basis
# double-count (see ``TASK_archetype_acquisition_double_count.md``)
# reappearing, not a wholesale write-down. Any test that only asserts
# "some sales are negative" cannot tell the two apart; the ceiling
# is what the reshaped assertion checks against.

_MAX_LOSER_LOSS: Decimal = Decimal("2500.00")
"""Cap on any single deliberate loser's negative gross.

A real "cut and move it" loss on a $10-15k used unit runs a few
hundred to a couple thousand dollars. Anything below -$2,500 is
almost certainly the archetype's acquisition-basis double-count
resurfacing, not a business decision. The ceiling is what
:mod:`test_seed_copper_canyon_auto_demo` uses to distinguish the
two — see the reshaped positive-gross assertion.
"""

_LOSER_REASON_AGED = "aged_out"
_LOSER_REASON_RECON_OVERRUN = "recon_overrun"
_LOSER_REASON_TRADE_OVERALLOWANCE = "trade_overallowance"
_LOSER_REASON_WHOLESALE_DISPOSAL = "wholesale_disposal"
_LOSER_REASON_PRICE_CONCESSION = "price_concession"


_DELIBERATE_LOSERS: tuple[dict, ...] = (
    # 1. The aged unit that finally moved. Its earliest frontline
    #    event is backdated to ~105 days by
    #    :func:`_backdate_aged_loser_frontline_events` so the vehicle
    #    lifecycle log reads "sat past 100 days" — the aging story the
    #    loss is the price of ignoring. Financed as BHPH: an aged unit
    #    finally moves for a subprime buyer with an in-house note.
    {
        "stock": "CC-060",
        "loss": Decimal("2200.00"),
        "reason": _LOSER_REASON_AGED,
        "delivery_notes": (
            "Sat 105 days at frontline before we cut the price to move "
            "it. Aging board had this one flagged for weeks; the loss "
            "is what ignoring it cost."
        ),
    },
    # 2. Recon overrun. Authorized $600 for a transmission flush,
    #    actual $1,900 once the shop opened the pan up. A completed
    #    WorkOrder with actual_cost above authorized shows on the
    #    vehicle's recon page; the sale row shows the loss the
    #    overrun caused. Retail — falls in the extension's retail
    #    finance-type band (offsets 8-24 → CC-031..CC-047).
    {
        "stock": "CC-041",
        "loss": Decimal("1800.00"),
        "reason": _LOSER_REASON_RECON_OVERRUN,
        "recon_authorized": Decimal("600.00"),
        "recon_actual": Decimal("1900.00"),
        "delivery_notes": (
            "Recon overrun — authorized $600 for the transmission "
            "flush, shop found the pan cracked. Actual came in at "
            "$1,900. Owner ate the delta rather than back out."
        ),
    },
    # 3. Trade overallowance. Front-end money we gave away to close
    #    the deal. Retail-financed — trades only make sense against a
    #    retail sale.
    {
        "stock": "CC-047",
        "loss": Decimal("1500.00"),
        "reason": _LOSER_REASON_TRADE_OVERALLOWANCE,
        "delivery_notes": (
            "Overallowance on the customer's trade to lock the deal. "
            "Book value ran $1,500 under what we credited."
        ),
    },
    # 4. Wholesale disposal (to auction). Terminal stage is
    #    wholesale_out — no retail delivery. Overridden to CASH
    #    finance-type because auction pays cash/wire; no lender.
    {
        "stock": "CC-053",
        "loss": Decimal("1200.00"),
        "reason": _LOSER_REASON_WHOLESALE_DISPOSAL,
        "delivery_notes": None,
    },
    # 5. Second wholesale disposal — a slower-turning unit that never
    #    generated a test drive. Same wholesale_out treatment.
    {
        "stock": "CC-058",
        "loss": Decimal("900.00"),
        "reason": _LOSER_REASON_WHOLESALE_DISPOSAL,
        "delivery_notes": None,
    },
    # 6. Price concession — the sales manager approved a $500 hair-
    #    cut on a car already priced thin. Small loss, common shape.
    #    CC-055 lands in the BHPH band; a concession-then-BHPH is a
    #    realistic close-a-subprime-deal move.
    {
        "stock": "CC-055",
        "loss": Decimal("500.00"),
        "reason": _LOSER_REASON_PRICE_CONCESSION,
        "delivery_notes": (
            "Sales manager approved a $500 concession at contract "
            "signing to keep the deal from walking. Front gross was "
            "already thin; concession pushed it below cost."
        ),
    },
)

_DELIBERATE_LOSER_STOCKS: frozenset[str] = frozenset(
    entry["stock"] for entry in _DELIBERATE_LOSERS
)
_DELIBERATE_LOSER_BY_STOCK: dict[str, dict] = {
    entry["stock"]: entry for entry in _DELIBERATE_LOSERS
}


def _seed_recon_overrun_wo(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    owner,
    authorized_cost: Decimal,
    actual_cost: Decimal,
) -> None:
    """Walk one WorkOrder for ``vehicle`` from draft to completed with
    ``actual_cost`` above ``authorized_cost``.

    Called from :func:`_extend_sales_history` for loser rows whose
    reason is ``recon_overrun`` — the completion posts a real
    :class:`VehicleCost` for the actual amount, which flows into
    :func:`compute_totals`, which drives the negative gross on the
    subsequent sale. The recon screen reads the ``actual`` /
    ``authorized`` split as the visible story.

    Creates a minimal :class:`ConditionReport` + :class:`ConditionFinding`
    on the vehicle first — ``approve_work_order`` refuses WOs without
    findings (see :mod:`dealer_ai.services.recon` docstring).
    """
    now = timezone.now()
    inspected_at = now - dt.timedelta(days=14)
    report = ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Miguel Ortega",
        inspected_at=inspected_at,
        mileage_at_inspection=vehicle.mileage or 90_000,
        status=CONDITION_REPORT_STATUS_COMPLETE,
        completed_at=inspected_at + dt.timedelta(hours=2),
        notes=(
            "Copper Canyon demo seed — recon inspection for "
            f"{vehicle.stock_number}."
        ),
    )
    finding = ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=(
            "Transmission flush + pan reseal. Estimate written against "
            "the flush only; if the pan is cracked when shop opens it, "
            "add the reseal."
        ),
    )
    vendor = Vendor.objects.filter(
        dealership=dealership, is_active=True
    ).order_by("pk").first()
    if vendor is None:  # pragma: no cover — archetype seeds a vendor
        return
    wo = create_work_order(
        vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        venue="outsourced",
        vendor=vendor,
        estimated_cost=authorized_cost,
        notes=(
            "Transmission service. Authorized against the flush estimate; "
            "actual came in over once the shop opened the pan."
        ),
    )
    attach_findings(wo, dealership=dealership, finding_ids=[finding.pk])
    approve_work_order(
        wo,
        dealership=dealership,
        approved_by=owner,
        authorized_cost=authorized_cost,
    )
    start_work_order(wo, dealership=dealership, started_by=owner)
    complete_work_order(
        wo,
        dealership=dealership,
        completed_by=owner,
        actual_cost=actual_cost,
        actual_completion_date=(now - dt.timedelta(days=2)).date(),
    )


def _transition_to_wholesale_out(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    entered_at: dt.datetime,
) -> None:
    """Move ``vehicle`` from its current stage to ``wholesale_out``
    directly, mirroring the model-direct pattern
    :func:`_expand_stage_distribution` uses.

    ``advance_stage`` refuses ``hold_reserved → wholesale_out`` — that
    is a seed-only side path — so we rewrite :class:`VehicleStage` +
    add a :class:`VehicleStageEvent` in one atomic slice. Called for
    losers whose reason is ``wholesale_disposal``, after
    :func:`record_sale` has stamped the vehicle at ``hold_reserved``.

    ``entered_at`` should be the sale date (or nearby) so
    :func:`_seed_stage_aging_snapshots` reads real days-since-sale
    on the wholesale_out column. Stamping now flattens the aging
    board for that stage — every historical snapshot would then see
    the newly-transitioned unit as "0 days" and drag the p50 down.
    """
    stage_row = VehicleStage.objects.filter(
        dealership=dealership, vehicle=vehicle
    ).first()
    if stage_row is None:  # pragma: no cover — record_sale creates one
        return
    previous = stage_row.current_stage
    # Backdate any prior event that would post-date the new
    # entered_at, so the vehicle's stage-event log stays
    # chronological (same invariant _distribute_lifecycle_stages
    # protects). record_sale stamps a ``hold_reserved`` event at
    # ``now``, which is later than the sale-date entered_at we are
    # about to write.
    prior_cutoff = entered_at - dt.timedelta(minutes=30)
    VehicleStageEvent.objects.filter(
        vehicle=vehicle,
        entered_at__gt=prior_cutoff,
    ).exclude(to_stage=VEHICLE_STAGE_WHOLESALE_OUT).update(
        entered_at=prior_cutoff,
    )
    stage_row.current_stage = VEHICLE_STAGE_WHOLESALE_OUT
    stage_row.entered_at = entered_at
    stage_row.trigger = VEHICLE_STAGE_TRIGGER_MANUAL
    stage_row.save(update_fields=["current_stage", "entered_at", "trigger"])
    VehicleStageEvent.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        from_stage=previous,
        to_stage=VEHICLE_STAGE_WHOLESALE_OUT,
        entered_at=entered_at,
        trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        notes=(
            "Copper Canyon demo seed — wholesale disposal (cut losses "
            "at auction rather than retail)."
        ),
    )


def _backdate_aged_loser_frontline_events(
    dealership: Dealership, stdout
) -> None:
    """For any deliberate loser tagged ``aged_out``, move the earliest
    ``to_stage=frontline`` VehicleStageEvent back to ~105 days ago.

    :func:`_backdate_frontline_events_for_sales` runs earlier in
    ``handle()`` and sets a 20–44 day spread; this replaces that value
    for the aged-loser stocks only, so the vehicle-lifecycle log reads
    as "sat past 100 days at frontline before we cut it." Idempotent.
    """
    now = timezone.now()
    target_days_ago = 105
    target = now - dt.timedelta(days=target_days_ago)
    updated = 0
    for entry in _DELIBERATE_LOSERS:
        if entry["reason"] != _LOSER_REASON_AGED:
            continue
        vehicle = Vehicle.objects.filter(
            dealership=dealership, stock_number=entry["stock"]
        ).first()
        if vehicle is None:
            continue
        earliest = (
            VehicleStageEvent.objects.filter(
                vehicle=vehicle, to_stage=VEHICLE_STAGE_FRONTLINE
            )
            .order_by("entered_at")
            .first()
        )
        if earliest is None or earliest.entered_at <= target:
            continue
        earliest.entered_at = target
        earliest.save(update_fields=["entered_at"])
        # Any earlier bootstrap event must move further back too so
        # the log stays chronological.
        VehicleStageEvent.objects.filter(
            vehicle=vehicle,
            trigger__in=("import", "bootstrap"),
            entered_at__gt=target,
        ).update(entered_at=target - dt.timedelta(hours=1))
        updated += 1
    stdout.write(
        f"backdated {updated} aged-loser frontline event(s) to ~"
        f"{target_days_ago} days ago."
    )

# Buyer names for the 38 extended-sales cohort. Yuma-shaped —
# consistent with the persona rename map. Rotated by index; longer
# than 38 in case future increments bump the sale count.
_EXTENDED_BUYER_NAMES: tuple[str, ...] = (
    "Adriana Peña", "Bryan Cortez", "Carla Ramirez", "Diego Salazar",
    "Elena Beltran", "Fernando Ochoa", "Gina Marquez", "Hector Delgado",
    "Iris Espinoza", "Javier Alcaraz", "Karina Vega", "Luis Contreras",
    "Marisol Nava", "Nestor Valenzuela", "Olivia Sanchez", "Pablo Rivas",
    "Quetzali Fuentes", "Ramon Bustos", "Sofia Escobedo", "Tomas Chavarria",
    "Ursula Padilla", "Vicente Cortés", "Wendy Guzman", "Xavier Munoz",
    "Yolanda Zamora", "Zeke Robles", "Amelia Diaz", "Bruno Herrera",
    "Camila Rojas", "Daniel Nguyen", "Estella Pham", "Felipe Torres",
    "Grace Wu", "Hugo Serrano", "Ines Villanueva", "Jorge Aguilar",
    "Kayla Reyes", "Leo Mendez",
)


def _extend_sales_history(
    dealership: Dealership, owner, stdout
) -> dict:
    """Book :data:`_EXTENDED_SALES_TOTAL` additional sales across the
    trailing 30 days, each through the real
    :func:`services.sale.record_sale` verb.

    Each sale then goes through :func:`record_delivery` so it lands
    at ``off_market`` — matching the pace-rule shape. BHPH sales get
    a :class:`BhphNote` originated via
    :func:`record_bhph_note` and a handful of weekly payments
    recorded via :func:`services.bhph_payments.record_payment`.

    Delivery date is capped at yesterday so no demo dates land in
    the future (same guard :func:`_deliver_five_sales` applies).

    Returns a summary dict with per-finance-type counts.
    """
    now = timezone.now()
    today = now.date()
    yesterday = today - dt.timedelta(days=1)

    # Pick 38 currently-unsold vehicles from the imported pool. Sort
    # by stock number so the assignment is deterministic across
    # re-runs. Exclude vehicles already in prep-adjacent stages —
    # a sold unit had to be at frontline first.
    candidates = list(
        Vehicle.objects.filter(
            dealership=dealership,
            sale__isnull=True,
            stage__current_stage=VEHICLE_STAGE_FRONTLINE,
            stock_number__startswith="CC-",
        )
        .select_related("stage")
        .order_by("stock_number")[: _EXTENDED_SALES_TOTAL]
    )
    if len(candidates) < _EXTENDED_SALES_TOTAL:
        stdout.write(
            f"WARN: only {len(candidates)} frontline CC-#### vehicles "
            f"available for {_EXTENDED_SALES_TOTAL} extension sales; "
            "skipping the rest — expand the import batch or reduce the "
            "sales target."
        )

    counts = {"cash": 0, "retail": 0, "bhph": 0}
    bhph_notes_created = 0
    bhph_payments_recorded = 0
    deliveries_recorded = 0

    losers_booked: list[dict] = []
    for offset, vehicle in enumerate(candidates):
        # Finance-type deal — first 8 cash, next 17 retail, last 13
        # BHPH. Deterministic assignment across re-runs.
        if offset < _EXTENDED_SALES_CASH:
            finance_type = SALE_FINANCE_TYPE_CASH
            lender_name = ""
        elif offset < _EXTENDED_SALES_CASH + _EXTENDED_SALES_RETAIL:
            finance_type = SALE_FINANCE_TYPE_RETAIL
            lender_name = "Sonoran Auto Finance"
        else:
            finance_type = SALE_FINANCE_TYPE_BHPH
            lender_name = ""

        # Deliberate-loser override — the six sales that lose money in
        # the trailing month. See :data:`_DELIBERATE_LOSERS`. Wholesale
        # disposals get forced to cash (auction pays cash/wire, no
        # lender); everything else keeps the pace-driven finance mix.
        loser = _DELIBERATE_LOSER_BY_STOCK.get(vehicle.stock_number)
        if loser is not None:
            if loser["reason"] == _LOSER_REASON_WHOLESALE_DISPOSAL:
                finance_type = SALE_FINANCE_TYPE_CASH
                lender_name = ""

        # Spread sale_date across the last 30 days so the trailing-
        # month analytics windows read a real distribution. Day 0 =
        # yesterday, day 29 = 30 days ago.
        days_since_sale = 1 + (offset * 30 // _EXTENDED_SALES_TOTAL)
        sale_date = today - dt.timedelta(days=days_since_sale)

        # Sold price. Winners sell at sticker (the archetype does the
        # same); losers price at a level that produces exactly the
        # loss the loser dict names. Purchase price = 60 % of sticker
        # per :func:`_extend_lot_to_target_size`, so:
        #   winner:            sold_price = sticker            → +40 %
        #   loser (non-recon): sold_price = purchase - loss    → -loss
        #   loser (recon):     sold_price = purchase           → -loss
        #                       (loss comes from actual_cost > 0)
        # Recon-overrun losers also complete a WorkOrder with
        # actual_cost = loss BEFORE record_sale, so total_investment
        # picks up the overrun via :func:`compute_totals`.
        purchase_price = (vehicle.price * Decimal("0.6")).quantize(
            Decimal("1.00")
        )
        if loser is None:
            sold_price = vehicle.price
        elif loser["reason"] == _LOSER_REASON_RECON_OVERRUN:
            _seed_recon_overrun_wo(
                vehicle,
                dealership=dealership,
                owner=owner,
                authorized_cost=loser["recon_authorized"],
                actual_cost=loser["recon_actual"],
            )
            # WO completion posts a VehicleCost for actual_cost, so
            # total_investment = purchase + actual. To land gross at
            # exactly -loss:
            #     sold_price = purchase + actual - loss
            # (Not purchase + authorized — that formulation left
            # gross = -(actual - authorized), which is only the
            # overrun delta, not the intended loss.)
            sold_price = (
                purchase_price + loser["recon_actual"] - loser["loss"]
            ).quantize(Decimal("1.00"))
        else:
            sold_price = (purchase_price - loser["loss"]).quantize(
                Decimal("1.00")
            )

        # Buyer as a walk-in lead so the deal has customer trail.
        buyer_name = _EXTENDED_BUYER_NAMES[offset % len(_EXTENDED_BUYER_NAMES)]
        buyer = CustomerLead.objects.create(
            dealership=dealership,
            name=buyer_name,
            email=synthetic_email(buyer_name),
            phone=f"928-555-{1000 + offset:04d}",
            urgency="immediate",
            channel="walk_in",
            created_at=now - dt.timedelta(days=days_since_sale + 1),
        )
        sale = record_sale(
            vehicle,
            dealership=dealership,
            sale_date=sale_date,
            sold_price=sold_price,
            finance_type=finance_type,
            buyer=buyer,
            lender_name=lender_name,
            posted_by_user=owner,
        )
        counts[finance_type] += 1
        if loser is not None:
            losers_booked.append(
                {
                    "stock": vehicle.stock_number,
                    "reason": loser["reason"],
                    "target_loss": loser["loss"],
                    "sale_pk": sale.pk,
                }
            )

        # BHPH note origination — the note books at sale time and
        # runs weekly for two years, mirroring the archetype
        # _extend_bhph_portfolio shape but at scale.
        if finance_type == SALE_FINANCE_TYPE_BHPH:
            first_payment_due = sale_date + dt.timedelta(days=7)
            note = record_bhph_note(
                dealership=dealership,
                sale=sale,
                principal_financed=vehicle.price,
                apr=Decimal("18.9"),
                term_weeks=104,
                payment_frequency="weekly",
                first_payment_due=first_payment_due,
            )
            bhph_notes_created += 1
            # Record 1 payment per full week between first_payment_due
            # and today. New notes carry no payments yet; older ones
            # accumulate a couple.
            weeks_paid = max(
                0, (today - first_payment_due).days // 7
            )
            for week_offset in range(min(weeks_paid, 4)):
                paid_at = now - dt.timedelta(
                    days=(weeks_paid - week_offset - 1) * 7
                )
                # Weekly payment approximated as principal / term_weeks
                # + APR component (rough; the deterministic BHPH
                # engine is the source of truth for real callers).
                weekly_payment = (
                    vehicle.price / Decimal("104")
                ).quantize(Decimal("1.00")) + Decimal("35.00")
                record_payment(
                    dealership=dealership,
                    note=note,
                    paid_at=paid_at,
                    amount=weekly_payment,
                    method=BHPH_PAYMENT_METHOD_CASH,
                )
                bhph_payments_recorded += 1

        # Wholesale disposal — no retail delivery. The vehicle moves
        # directly from hold_reserved → wholesale_out. Cutting losses
        # at auction is the classic "we ate this one" shape a dealer
        # will recognise on the aging board. Stamp the transition at
        # the sale date so the wholesale_out aging column doesn't
        # collapse to zero when snapshots backfill.
        if (
            loser is not None
            and loser["reason"] == _LOSER_REASON_WHOLESALE_DISPOSAL
        ):
            wholesale_entered_at = dt.datetime.combine(
                sale_date, dt.time(15, 0), tzinfo=dt.timezone.utc
            )
            _transition_to_wholesale_out(
                vehicle,
                dealership=dealership,
                entered_at=wholesale_entered_at,
            )
            continue

        # Delivery — every non-wholesaled extension sale is delivered.
        # Delivery date is 1-4 days after sale, capped at yesterday.
        # Loser delivery notes carry the loss narrative (aged /
        # recon overrun / trade overallowance / price concession) so
        # the sale row's negative gross has a matching story in the
        # delivery record.
        delivery_lag_days = 1 + (offset % 4)
        delivery_date = sale_date + dt.timedelta(days=delivery_lag_days)
        if delivery_date > yesterday:
            delivery_date = yesterday
        default_notes = (
            "Copper Canyon demo seed — extended sales history delivery."
        )
        delivery_notes = (
            (loser or {}).get("delivery_notes") or default_notes
        )
        # Only record the delivery if the vehicle is currently at
        # ``hold_reserved`` (the state ``record_sale`` puts it in).
        # If a prior partial run already delivered it, skip.
        current_stage = get_current_stage(vehicle, dealership=dealership)
        if (
            current_stage is not None
            and current_stage.current_stage == VEHICLE_STAGE_HOLD_RESERVED
            and not Delivery.objects.filter(sale=sale).exists()
        ):
            record_delivery(
                vehicle,
                dealership=dealership,
                delivery_date=delivery_date,
                temp_tag_number=f"TT-{vehicle.stock_number}",
                notes=delivery_notes,
            )
            deliveries_recorded += 1

    loser_summary = ", ".join(
        f"{row['stock']}={row['reason']}(-${row['target_loss']})"
        for row in losers_booked
    ) or "none"
    stdout.write(
        f"extended sales history: booked "
        f"cash={counts['cash']}, retail={counts['retail']}, "
        f"bhph={counts['bhph']} sale(s); "
        f"created {bhph_notes_created} BHPH note(s) with "
        f"{bhph_payments_recorded} payment(s); "
        f"recorded {deliveries_recorded} deliveries; "
        f"deliberate losers: {loser_summary}."
    )
    return {
        "sales_by_type": counts,
        "bhph_notes": bhph_notes_created,
        "bhph_payments": bhph_payments_recorded,
        "deliveries": deliveries_recorded,
        "losers_booked": losers_booked,
    }


# ---------------------------------------------------------------------------
# Deal writeup — one approved four-square so the writeup list endpoint
# returns something.
# ---------------------------------------------------------------------------


def _seed_deal_writeup(
    dealership: Dealership, owner, stdout
) -> int | None:
    """Write one approved :class:`DealWriteup` for a real lead + vehicle.

    Pairs an existing assigned CustomerLead with an unsold frontline
    vehicle. Approves the writeup so the "approved but not yet handed
    off" filter on the list endpoint has a positive row.
    """
    lead = (
        CustomerLead.objects.filter(
            dealership=dealership, assigned_to__isnull=False
        )
        .order_by("pk")
        .first()
    )
    if lead is None:
        stdout.write("no assigned lead for deal writeup; skipping.")
        return None
    # Any unsold vehicle works — the writeup is a customer-side
    # worksheet, not a stage-gated action. Frontline is preferred if
    # available; fall back to any unsold vehicle so the extension
    # steps that consume frontline stock (BHPH + F&I) do not starve
    # this one.
    vehicle = (
        Vehicle.objects.filter(
            dealership=dealership, sale__isnull=True,
            stage__current_stage=VEHICLE_STAGE_FRONTLINE,
        )
        .order_by("pk")
        .first()
    )
    if vehicle is None:
        vehicle = (
            Vehicle.objects.filter(
                dealership=dealership, sale__isnull=True,
            )
            .exclude(stage__current_stage=VEHICLE_STAGE_OFF_MARKET)
            .exclude(stage__current_stage=VEHICLE_STAGE_WHOLESALE_OUT)
            .order_by("pk")
            .first()
        )
    if vehicle is None:
        stdout.write("no unsold vehicle for deal writeup; skipping.")
        return None
    writeup = record_deal_writeup(
        dealership=dealership,
        lead=lead,
        vehicle=vehicle,
        written_up_by_user=owner,
        vehicle_price=Decimal("11795.00"),
        trade_allowance=Decimal("2500.00"),
        down_payment=Decimal("1500.00"),
        monthly_payment_target=Decimal("245.00"),
        term_months_target=60,
        apr_target=Decimal("14.9"),
        notes=(
            "Customer accepted the four-square. Waiting on trade-in "
            "appraisal to firm the numbers."
        ),
    )
    approve_deal_writeup(writeup=writeup, approved_by_user=owner)
    stdout.write(f"seeded deal writeup pk={writeup.pk} (approved).")
    return writeup.pk


# ---------------------------------------------------------------------------
# SLA breach — one outsourced WO approved 8 days ago, still in progress
# ---------------------------------------------------------------------------


def _seed_sla_stale_wo(
    dealership: Dealership, owner, stdout
) -> int | None:
    """Create one outsourced WO that is approved > 7 days ago and still
    in progress — landing in ``services.vendor_sla.detection`` as a
    stale-approval breach.

    Threshold: :data:`vendor_sla.detection.APPROVED_STALE_THRESHOLD_DAYS`
    (7 days). Backdating ``approved_at`` to 8 days ago puts the WO
    over the line by exactly one day.
    """
    now = timezone.now()
    vendor = Vendor.objects.filter(
        dealership=dealership,
        is_active=True,
    ).order_by("pk").first()
    if vendor is None:
        stdout.write("no active vendor for SLA-stale WO; skipping.")
        return None
    # Need a vehicle with at least one ConditionFinding available so
    # attach_findings has something to link (approve_work_order refuses
    # WOs with no findings; see services/recon.py:1120). Archetype
    # recon vehicles (RS-04, RS-07, RS-17) carry findings. RS-07 and
    # RS-17 already back the two awaiting-authorization drafts, so use
    # RS-04 — which the archetype already has an in-progress WO on but
    # that does not prevent a second WO on the same vehicle (multiple
    # findings can be handled in parallel).
    vehicle = None
    findings = []
    for stock in ("RS-04", "RS-07", "RS-17"):
        candidate = Vehicle.objects.filter(
            dealership=dealership, stock_number=stock
        ).first()
        if candidate is None:
            continue
        unclaimed = list(
            ConditionFinding.objects.filter(
                report__vehicle=candidate
            ).exclude(work_order_links__isnull=False).order_by("pk")
        )
        if unclaimed:
            vehicle = candidate
            findings = unclaimed[:1]
            break
    if vehicle is None or not findings:
        stdout.write(
            "no vehicle with an unclaimed finding for SLA-stale WO; skipping."
        )
        return None
    wo = create_work_order(
        vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        venue="outsourced",
        vendor=vendor,
        estimated_cost=Decimal("850.00"),
        notes=(
            "Outsourced brake work. Vendor confirmed but has not "
            "returned the vehicle — chase this."
        ),
    )
    attach_findings(
        wo,
        dealership=dealership,
        finding_ids=[findings[0].pk],
    )
    approve_work_order(
        wo,
        dealership=dealership,
        approved_by=owner,
        authorized_cost=Decimal("850.00"),
    )
    # Backdate approved_at to 8 days ago so the WO is over the 7-day
    # SLA threshold. Also backdate created_at so the aging read is
    # consistent (created before approved, per M4 invariants).
    approved_eight_days = now - dt.timedelta(days=8)
    WorkOrder.objects.filter(pk=wo.pk).update(
        created_at=approved_eight_days - dt.timedelta(hours=2),
        approved_at=approved_eight_days,
    )
    stdout.write(
        f"seeded SLA-stale outsourced WO pk={wo.pk} approved 8 days ago."
    )
    return wo.pk


# ---------------------------------------------------------------------------
# SLA breach materialization — run the M7.4 detection verb so
# SlaBreachRecord rows exist for the /admin/analytics/sla-breach-
# patterns/ endpoint to read.
# ---------------------------------------------------------------------------


def _materialize_sla_breaches(
    dealership: Dealership, stdout
) -> int:
    """Run :func:`services.vendor_sla.detection.detect_sla_breaches` for
    the tenant so the stale outsourced WO seeded by
    :func:`_seed_sla_stale_wo` shows up as an :class:`SlaBreachRecord`.

    The C1 review (2026-09-01) found
    ``/admin/analytics/sla-breach-patterns/`` returning
    ``total_breach_count=0`` even though ``detect_sla_breaches``
    reported one approved-stale breach when called live. Cause: the
    verb computes live and *also* materializes ``SlaBreachRecord`` via
    ``_materialize_breach_record`` (M8.1 addition per
    ``MILESTONE_8_PLANNING.md`` §5.b Option B); the endpoint reads the
    persisted rows, but nothing in the seed had ever called the verb,
    so the table was empty. In prod, the M7.4 Celery orchestrator runs
    at 04:00 daily — none of that is running during a fresh seed.

    Same relationship as :func:`_seed_stage_aging_snapshots` and the
    aging-trend endpoint: the seed composes existing verbs to make the
    materialized read-model non-empty. Idempotent — the verb's
    ``get_or_create`` on
    ``(work_order, kind, detected_at_date)`` no-ops on re-run.

    Returns the number of :class:`SlaBreachRecord` rows the invocation
    added (equal to ``report.breach_count`` on a fresh DB;
    zero on re-run).
    """
    report = detect_sla_breaches(dealership)
    stdout.write(
        f"materialized SLA breaches: "
        f"approved_stale={report.approved_stale_count}, "
        f"in_progress_past_eta={report.in_progress_past_eta_count} "
        f"(total={report.breach_count})."
    )
    return report.breach_count


# ---------------------------------------------------------------------------
# Buyer-estimate accuracy — put a buyer on one acquisition so the
# analytics endpoint has an attributable row.
# ---------------------------------------------------------------------------


def _seed_buyer_estimate_accuracy(
    dealership: Dealership, owner, stdout
) -> int | None:
    """Attribute the archetype's completed-recon acquisitions to a
    buyer so ``services/analytics/recon.py:buyer_estimate_accuracy``
    can compute a row for them.

    The archetype creates VehicleAcquisition rows with ``buyer=None``.
    Analytics excludes those to avoid an "anonymous buyer" bucket.
    Backfill ``buyer=owner`` on the acquisitions for the vehicles
    whose WOs were completed by ``_complete_recon_work_orders`` (those
    are the WOs with both ``estimated_cost`` + ``actual_cost``, the
    only rows that contribute to accuracy).
    """
    completed_vehicles = list(
        Vehicle.objects.filter(
            dealership=dealership,
            work_orders__status="completed",
            work_orders__estimated_cost__isnull=False,
            work_orders__actual_cost__isnull=False,
        ).distinct()
    )
    if not completed_vehicles:
        stdout.write("no completed WOs with cost data; skipping buyer estimate.")
        return None
    updated = VehicleAcquisition.objects.filter(
        dealership=dealership,
        vehicle__in=completed_vehicles,
    ).update(buyer=owner)
    stdout.write(
        f"attributed {updated} acquisition(s) to buyer={owner.username!r} "
        "so buyer-estimate-accuracy has a computable row."
    )
    return owner.pk
