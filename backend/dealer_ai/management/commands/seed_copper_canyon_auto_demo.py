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
    CONTRACT_TYPE_RISC,
    CREDIT_APP_FORMAT_TABLET,
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    LENDER_SUBMISSION_STATUS_APPROVED,
    LENDER_SUBMISSION_STATUS_PENDING,
    ROLE_DEALER_OWNER,
    SALE_FINANCE_TYPE_BHPH,
    STIP_TYPE_PROOF_OF_INCOME,
    VEHICLE_STAGE_COMPANY_USE,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_LISTING,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_QC,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    VEHICLE_STAGE_WHOLESALE_OUT,
    BhphNote,
    ChatMessage,
    ChatSession,
    ConditionFinding,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealerOnboardingProfile,
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
from dealer_ai.services.lifecycle_aging.snapshots import snapshot_stage_ages
from dealer_ai.services.vendor_sla.detection import detect_sla_breaches
from dealer_ai.services.sale.computation import gross_realized
from dealer_ai.services.vehicle_lifecycle import advance_stage, get_current_stage
from dealer_ai.services.recon import (
    approve_work_order,
    attach_findings,
    complete_work_order,
    create_work_order,
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
    # RS-06 and RS-08 stay at their post-archetype frontline stage
    # so the frontline aging board reads a plausible unsold spread;
    # DETAIL and PHOTOGRAPHY lose their single-slot demo signal as a
    # trade-off, given the archetype only ships 20 vehicles.
    # WHOLESALE_OUT loses its single-slot signal for the same reason
    # (RS-15 was sold retail and cannot semantically sit there).
    (VEHICLE_STAGE_INCOMING, ("RS-01", "RS-02"), 2),
    (VEHICLE_STAGE_INSPECTION, ("RS-03",), 4),
    # RS-04, RS-07, RS-17 stay at recon (archetype).
    (VEHICLE_STAGE_QC, ("RS-05",), 7),
    (VEHICLE_STAGE_LISTING, ("RS-09",), 13),
    # RS-06 (detail) + RS-08 (photography) intentionally omitted so
    # they stay at frontline post-archetype as unsold aging demo units.
    (VEHICLE_STAGE_COMPANY_USE, ("RS-18",), 100),
    (VEHICLE_STAGE_OFF_MARKET, ("RS-19", "RS-20"), 35),
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
            _backdate_frontline_stage_aging(dealership, self.stdout)
            _backdate_hold_reserved_for_sales(dealership, self.stdout)
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
                f"bhph_notes={bhph_summary}, "
                f"fni={fni_summary}, "
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
_FRONTLINE_AGING_DAYS_UNSOLD: tuple[int, ...] = (4, 15, 33, 62, 95)


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

    # Mirror the ``record_sale`` lifecycle hook by hand — this helper
    # writes the Sale directly (see class docstring) so the sale-hook
    # side effect must be re-composed here. Otherwise the extension's
    # sold BHPH units would sit on frontline forever.
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
