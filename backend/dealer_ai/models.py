import uuid
from datetime import date
from decimal import Decimal
from functools import cached_property
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


# Milestone 1 · Increment 4A — role vocabulary. Kept as a module-level
# constant so subsequent increments (4B request-context tenancy resolver,
# 4C advisor workspace auth, 4D admin gating) import the canonical list
# without re-declaring the string literals. Source of truth:
# ``docs/roadmap/IMPLEMENTATION_ROADMAP.md`` §Milestone 1.
ROLE_DEALER_OWNER = "dealer_owner"
ROLE_SALES_MANAGER = "sales_manager"
ROLE_RECON_MANAGER = "recon_manager"
ROLE_F_AND_I_MANAGER = "f_and_i_manager"
ROLE_COLLECTIONS = "collections"
ROLE_ADVISOR = "advisor"
ROLE_PORTER = "porter"

ROLE_CHOICES = (
    (ROLE_DEALER_OWNER, "Dealer owner"),
    (ROLE_SALES_MANAGER, "Sales manager"),
    (ROLE_RECON_MANAGER, "Recon manager"),
    (ROLE_F_AND_I_MANAGER, "F&I manager"),
    (ROLE_COLLECTIONS, "Collections"),
    (ROLE_ADVISOR, "Advisor"),
    (ROLE_PORTER, "Porter"),
)


class Dealership(models.Model):
    """Tenancy root introduced in Milestone 1.

    Every data-carrying model (Vehicle, ChatSession, ChatMessage,
    CustomerLead, Salesperson, DealerOnboardingProfile) will gain a
    ``dealership`` FK pointing here in subsequent Milestone 1 increments.
    Introduced first, in isolation, so the FK-carrier work in later
    increments has a real target row to reference and the backfill has
    somewhere to point.

    ``slug`` is the stable identifier used by request-context resolution
    (subsequent increments will resolve tenant from an incoming header
    or the authenticated user's dealership). Kept unique.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Vehicle(models.Model):
    CONDITION_CHOICES = [
        ("new", "New"),
        ("used", "Used"),
        ("certified", "Certified Pre-Owned"),
    ]

    BODY_STYLE_CHOICES = [
        ("truck", "Truck"),
        ("suv", "SUV"),
        ("car", "Car"),
        ("ev", "EV"),
        ("van", "Van"),
    ]

    # Milestone 1 · Increment 3 — tenancy FK, NOT NULL. Every write
    # path either passes ``dealership=`` explicitly or is caught by the
    # ``pre_save`` fallback registered in
    # :mod:`services.tenancy` (attaches the default row). Existing
    # unique constraint on ``stock_number`` preserved (tenant-scoped
    # ``(dealership, stock_number)`` unique is a later increment).
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    stock_number = models.CharField(max_length=32, unique=True)
    vin = models.CharField(max_length=32, blank=True)
    year = models.PositiveIntegerField()
    make = models.CharField(max_length=64, default="Ford")
    model = models.CharField(max_length=64)
    trim = models.CharField(max_length=128, blank=True)
    body_style = models.CharField(max_length=16, choices=BODY_STYLE_CHOICES, default="suv")
    condition = models.CharField(max_length=16, choices=CONDITION_CHOICES, default="new")
    mileage = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    msrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    exterior_color = models.CharField(max_length=64, blank=True)
    interior_color = models.CharField(max_length=64, blank=True)
    drivetrain = models.CharField(max_length=32, blank=True)
    transmission = models.CharField(max_length=32, blank=True)
    fuel_type = models.CharField(max_length=32, blank=True, default="Gasoline")
    engine = models.CharField(max_length=128, blank=True)
    features = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    url = models.URLField(blank=True)
    is_available = models.BooleanField(default=True)
    # Import provenance — set by management/commands/import_inventory.py
    # (or seed_demo_vehicles for the bundled demo set).
    source = models.CharField(max_length=64, blank=True, default="")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "model"]

    def __str__(self) -> str:
        return f"{self.year} {self.make} {self.model} {self.trim} (#{self.stock_number})"

    @property
    def display_name(self) -> str:
        parts = [str(self.year), self.make, self.model, self.trim]
        return " ".join(p for p in parts if p)

    # ---- Milestone 2 · Increment 3 — Vehicle-as-read-model -------------
    #
    # The following properties are the *read model* for the Vehicle
    # Investment Ledger. Callers (Django admin, future serializers,
    # future ledger UI) can read financial totals off a ``Vehicle``
    # instance without knowing anything about how the ledger is
    # implemented.
    #
    # Layer contract (see also ``docs/roadmap/MILESTONE_2_PLANNING.md``
    # §1.3 + §7.b · M2.3):
    #
    # - ``Vehicle`` = read model. Thin delegator. Never aggregates.
    #   Never understands cost categories. Never writes.
    # - ``services/vehicle_ledger.py`` = business layer + write model.
    #   All aggregation, category grouping, and money math lives
    #   there. All writes go through ``record_acquisition`` /
    #   ``add_cost``.
    #
    # Caching contract:
    #
    # - :attr:`ledger_totals` is a ``@cached_property`` — the first
    #   read triggers exactly one ledger computation (six DB queries;
    #   see ``compute_totals`` docstring). Every subsequent read on
    #   the same instance returns from cache (zero queries).
    # - The nine per-total properties (`total_investment`,
    #   `projected_total_investment`, etc.) all delegate to the
    #   cached ``ledger_totals`` object. Reading all nine costs the
    #   same as reading one.
    # - :attr:`days_in_inventory` is a plain ``@property`` — it does
    #   not go through ``ledger_totals`` because it is a temporal
    #   metric (depends on "today"), not a financial one. Django's
    #   OneToOne reverse-accessor cache means both properties share
    #   the same acquisition lookup after either one runs, so
    #   reading both together does not double-query.
    #
    # Cache invalidation caveat: writes made *after* a
    # ``ledger_totals`` read on the same instance are NOT reflected
    # in the cached value. Callers that write via
    # :func:`services.vehicle_ledger.add_cost` and then read totals
    # on the same instance should either refetch the Vehicle
    # (``Vehicle.objects.get(pk=...)``) or delete the cached
    # attribute (``del vehicle.ledger_totals``) before reading. In
    # the request/response cycle this is not a concern — each
    # request builds a fresh Vehicle instance from the DB.

    @cached_property
    def ledger_totals(self):
        """Cached snapshot of the vehicle's ledger totals.

        Runs ``services.vehicle_ledger.compute_totals`` exactly once
        per Vehicle instance and caches the returned
        :class:`services.vehicle_ledger.LedgerTotals`. Every
        downstream property reads a field off this cached instance
        instead of re-querying.

        Tenant resolves from ``self.dealership`` — the vehicle
        borrows its own tenant. Cross-tenant leakage is impossible
        here because the vehicle IS in its dealership by
        construction; the service-layer ``CrossTenantLedgerError``
        would only fire if a caller manually mutated
        ``vehicle.dealership_id`` in memory to a different value
        before reading a property. Locked by
        ``VehicleReadModelTenantIsolation``.
        """
        # Local import — the ledger service imports models, so a
        # top-of-module import here would create a cycle at import
        # time. Django handles this pattern throughout the codebase
        # (see ``services/tenancy.py`` for the same guard).
        from .services.vehicle_ledger import compute_totals

        return compute_totals(self, dealership=self.dealership)

    @property
    def total_investment(self):
        """Money actually committed to this vehicle.

        Equals ``acquisition_total + actual_cost_total``. Excludes
        rows where ``is_estimate=True``. This is the number to
        compare against the asking price for projected front-end
        gross. See the module docstring in
        ``services/vehicle_ledger.py`` for the load-bearing
        semantic contract.
        """
        return self.ledger_totals.total_investment

    @property
    def projected_total_investment(self):
        """Money in this vehicle once every open estimate lands.

        Equals ``total_investment + estimated_cost_total``. Useful
        for pricing decisions; NOT for sunk-cost comparisons
        (would double-count projected spend as invested).
        """
        return self.ledger_totals.projected_total_investment

    @property
    def acquisition_total(self):
        """Sum of every cash line on the acquisition row.

        Returns :data:`services.vehicle_ledger.ZERO` when no
        acquisition record exists.
        """
        return self.ledger_totals.acquisition_total

    @property
    def actual_cost_total(self):
        """Sum of category totals for actual (``is_estimate=False``)
        costs across flooring + recon + admin + photography."""
        return self.ledger_totals.actual_cost_total

    @property
    def estimated_cost_total(self):
        """Sum of ``VehicleCost.amount`` across every category where
        ``is_estimate=True``. Money projected but not committed."""
        return self.ledger_totals.estimated_cost_total

    @property
    def flooring_total(self):
        """Actual flooring costs (``is_estimate=False``). Category
        partition lives in
        :data:`dealer_ai.models.FLOORING_CATEGORIES`."""
        return self.ledger_totals.flooring_total

    @property
    def recon_total(self):
        """Actual reconditioning costs (``is_estimate=False``).
        Category partition lives in
        :data:`dealer_ai.models.RECON_CATEGORIES`."""
        return self.ledger_totals.recon_total

    @property
    def administrative_total(self):
        """Actual administrative costs (``is_estimate=False``).
        Category partition lives in
        :data:`dealer_ai.models.ADMIN_CATEGORIES`."""
        return self.ledger_totals.administrative_total

    @property
    def photography_total(self):
        """Actual photography costs (``is_estimate=False``). Kept
        separate from administrative so future photography
        surfaces can distinguish 'shot for listing' from 'shot
        for damage documentation' without recategorizing history.
        Category partition lives in
        :data:`dealer_ai.models.PHOTOGRAPHY_CATEGORIES`."""
        return self.ledger_totals.photography_total

    @property
    def days_in_inventory(self) -> Optional[int]:
        """Days elapsed since the vehicle was physically acquired.

        Primary signal: ``VehicleAcquisition.purchase_date``.
        Returns ``today - purchase_date`` in whole days (never
        negative — a future purchase_date returns 0, which
        surfaces the operator's data-entry error without breaking
        aging math).

        **Fallback behavior when no acquisition record exists:**
        returns ``None``. Aging is undefined until the operator
        records the acquisition. A misleading fallback (e.g.
        ``imported_at`` when the vehicle was imported via CSV
        weeks after physical arrival) would produce wrong aging
        buckets in the ledger UI. ``None`` forces the operator
        to record the acquisition first — a documented invariant
        of Milestone 2's ledger model.

        Timezone: uses ``django.utils.timezone.now().date()`` for
        "today", which respects ``settings.TIME_ZONE``
        (``America/Chicago``). Comparing a
        timezone-aware "now" against a ``purchase_date`` (a naive
        :class:`datetime.date`) is safe because ``.date()`` strips
        the timezone.
        """
        purchase_date = self._purchase_date_or_none()
        if purchase_date is None:
            return None
        today = timezone.now().date()
        delta_days = (today - purchase_date).days
        return max(0, delta_days)

    def _purchase_date_or_none(self) -> Optional[date]:
        """Return ``VehicleAcquisition.purchase_date`` or ``None``.

        Wrapped for testability + to isolate the OneToOne reverse-
        accessor + ``DoesNotExist`` handling in one place. Django
        caches the OneToOne reverse access on the Vehicle instance,
        so calling this after :attr:`ledger_totals` (which also
        accesses ``self.acquisition``) does not re-query.

        Note: ``VehicleAcquisition`` is defined below in this same
        module. At method-call time the class already exists in
        module scope; the reference resolves fine.
        """
        try:
            return self.acquisition.purchase_date
        except VehicleAcquisition.DoesNotExist:
            return None

    # ---- Milestone 3 · Increment 3 — Vehicle-as-condition-report-read-model
    #
    # Two thin ``@property`` delegators to
    # :mod:`services.condition_report`. Callers holding a
    # ``Vehicle`` instance can ask "what is the current inspection
    # state of this stock number?" without knowing that
    # :class:`ConditionReport` exists as a distinct row.
    #
    # Layer contract (mirrors the M2.3 ledger read-model above):
    #
    # - ``Vehicle`` = read model. Thin delegator. Never filters,
    #   orders, aggregates, or caches. Never writes.
    # - ``services/condition_report.py`` = business layer + write
    #   model. All query shape, ordering, tenant guards, and state
    #   transitions live there.
    #
    # Caching contract:
    #
    # - Both properties are plain ``@property`` — **not**
    #   ``@cached_property``. Rationale: the M2.3
    #   :attr:`ledger_totals` cached-property pattern is proven for
    #   read-heavy repeated-access data (nine per-total delegators
    #   would otherwise fire nine queries against the ledger). The
    #   condition-report accessors are lighter — the operator UI
    #   reads at most both once per page load — and the natural
    #   query profile deserves to be measured before optimization.
    #   If subsequent operator UI work reveals repeated access on
    #   the same instance, promote to ``@cached_property`` with
    #   evidence rather than assumption. Locked by the
    #   ``assertNumQueries(1)`` tests in
    #   ``tests/test_vehicle_condition_report_properties.py``.
    #
    # See ``docs/roadmap/MILESTONE_3_PLANNING.md`` §1.3 + §7 M3.3
    # for the design memo.

    @property
    def latest_condition_report(self):
        """The most recent condition report for this vehicle, or
        ``None`` if the vehicle has never been inspected.

        Any status (``draft`` or ``complete``). Deterministic
        ordering — matches the underlying service function's
        ``(-inspected_at, -created_at)`` sort.

        Tenant resolves from ``self.dealership`` — the vehicle
        borrows its own tenant. Cross-tenant leakage is impossible
        here by construction (a vehicle IS in its dealership); the
        service-layer ``CrossTenantConditionReportError`` would
        only fire if a caller manually mutated
        ``vehicle.dealership_id`` in memory to a different value
        before reading this property.
        """
        # Local import — ``services/condition_report.py`` imports
        # ``ConditionReport`` from this module, so a top-of-module
        # import here would create a cycle at import time. Same
        # guard as :attr:`ledger_totals` above (M2.3 pattern) and
        # ``services/tenancy.py``.
        from .services.condition_report import latest_condition_report

        return latest_condition_report(self, dealership=self.dealership)

    @property
    def latest_completed_condition_report(self):
        """The most recent *completed* condition report for this
        vehicle, or ``None`` if the vehicle has no signed-off
        inspection yet.

        Filtered to ``status="complete"`` — the accessor the M4
        recon-plan drafting and the M3.7 operator UI's "inspected
        on YYYY-MM-DD" badge will hit most often, because a draft
        report has not been signed off yet.

        Same ordering, tenant-resolution, and no-caching contract
        as :attr:`latest_condition_report`.
        """
        # Local import — see :attr:`latest_condition_report` for
        # the cycle rationale.
        from .services.condition_report import (
            latest_completed_condition_report,
        )

        return latest_completed_condition_report(
            self, dealership=self.dealership
        )

    # Milestone 4 · Increment 2 (SESSION_067) — recon read model
    # extension. Two `@property` accessors delegating to the recon
    # service, mirroring the M3.3 pattern above (function-local
    # imports; one-line delegation; no caching; no business logic
    # on the Vehicle side). Design memo in
    # ``docs/roadmap/MILESTONE_4_PLANNING.md`` §1.7.

    @property
    def open_work_orders(self):
        """Queryset of open :class:`WorkOrder` rows on this vehicle.

        "Open" means ``status`` is one of ``draft``, ``approved``,
        or ``in_progress`` — terminal statuses (``completed`` /
        ``cancelled``) are excluded. Deterministic ordering by
        ``-created_at`` matches the M4.1 model default so the
        M4.7 operator UI renders in a stable order.

        Tenant scoping resolved via ``self.dealership`` — mirrors
        the M3.3 read-model pattern (:attr:`latest_condition_report`).
        No caching; each attribute read runs a fresh query so
        callers see the current DB state after a transition.
        """
        # Local import — the recon service imports models from this
        # module, so a top-of-module import here would create a
        # cycle at import time. Same guard as
        # :attr:`latest_condition_report` (M3.3 pattern).
        from .services.recon import open_work_orders_for_vehicle

        return open_work_orders_for_vehicle(self, dealership=self.dealership)

    @property
    def has_recon_decisions(self):
        """``True`` iff this vehicle's latest completed condition
        report has at least one :class:`ReconDecision` attached.

        Cheap: the backing service function uses ``.exists()`` and
        does not load any Finding or ReconDecision instance into
        memory. Returns ``False`` when the vehicle has never been
        inspected, when its latest report is still ``draft``, or
        when no decisions have been recorded yet.

        Tenant scoping and no-caching contract mirror
        :attr:`open_work_orders` and :attr:`latest_condition_report`.
        """
        from .services.recon import has_recon_decisions_for_vehicle

        return has_recon_decisions_for_vehicle(
            self, dealership=self.dealership
        )

    # ----------------------------------------------------------------
    # Milestone 5 · Increment 2 (SESSION_076) — vehicle-lifecycle
    # read-model extension. Two `@property` accessors delegating to
    # the lifecycle service, mirroring the M3.3 / M4.7 pattern above
    # (function-local imports; one-line delegation; no caching; no
    # business logic on the Vehicle side).
    #
    # **Pure reads.** Neither property creates a stage row on first
    # access (SESSION_075 §0.a item 6 — no hidden writes from
    # Vehicle read-model properties). ``current_stage`` may return
    # ``None`` when no stage row exists;
    # ``is_retail_eligible`` returns ``False`` in that case.
    # Callers who need a stage row to definitely exist invoke
    # ``ensure_current_stage(...)`` explicitly — that is the M5.2
    # service's one mutating verb for lifecycle bootstrap.
    # ----------------------------------------------------------------

    @property
    def current_stage(self):
        """This vehicle's :class:`VehicleStage` row, or ``None``.

        **Pure read** — never creates a stage row on first access.
        Callers must handle the ``None`` case (a vehicle without a
        stage row is a real state, not an error). Migration
        ``0017`` bootstraps every Vehicle that existed at M5.1
        release; the M5.5 write-path integration will seed newly
        created vehicles with ``incoming`` via an explicit
        ``ensure_current_stage(...)`` call.

        Tenant scoping resolved via ``self.dealership``. No caching
        — each attribute read runs a fresh query so callers see
        the current DB state after a transition.
        """
        from .services.vehicle_lifecycle import get_current_stage

        return get_current_stage(self, dealership=self.dealership)

    @property
    def is_retail_eligible(self):
        """``True`` iff the vehicle's current lifecycle stage is
        ``frontline``.

        **Pure read** — returns ``False`` when no stage row exists.
        The M5.5 retail-gating refactor swaps
        ``services/chat_engine.py``,
        ``services/inventory_search.py``, and the public
        ``/showroom`` endpoint from ``is_available=True`` filters
        to ``is_retail_eligible=True`` (via a queryset annotation
        that joins ``VehicleStage.current_stage='frontline'``).

        ``Vehicle.is_available`` is retained for backwards
        compatibility per MILESTONE_5_PLANNING.md §5.e Option D
        (SESSION_075 refined) and MUST NOT be used as a manual
        override for retail gating — customer-facing eligibility
        comes from lifecycle stage alone.
        """
        from .services.vehicle_lifecycle import retail_eligible

        return retail_eligible(self, dealership=self.dealership)


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Milestone 1 · Increment 3 — tenancy FK, NOT NULL. Auto-attached by
    # the pre_save fallback in :mod:`services.tenancy` when the caller
    # leaves it unset; explicit ``dealership=`` short-circuits the fallback.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    customer_name = models.CharField(max_length=128, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    # Free-form session metadata (e.g. UTM, page, channel).
    metadata = models.JSONField(default=dict, blank=True)
    # Structured intent profile, merged across turns by intent_parser.
    extracted_profile = models.JSONField(default=dict, blank=True)
    lead_created = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ChatSession {self.id}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
        ("tool", "Tool"),
    ]

    # Milestone 1 · Increment 3 — tenancy FK, NOT NULL. Denormalized on
    # child rows for tenant-scoped read paths. The pre_save fallback in
    # :mod:`services.tenancy` inherits from the parent
    # :class:`ChatSession` when the caller leaves ``dealership`` unset,
    # keeping parent/child tenancy consistent without per-caller taxes.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    matched_vehicles = models.ManyToManyField(
        Vehicle, blank=True, related_name="chat_mentions"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        snippet = self.content[:60].replace("\n", " ")
        return f"[{self.role}] {snippet}"


class Salesperson(models.Model):
    """Manager Phase 4: dealership advisor profile.

    Used by:
      - the manager-side assignment dropdown (LeadDetailModal),
      - the public-facing "Meet the team" page,
      - the per-advisor workspace at ``/dealer-ai-advisor/<slug>``.

    Inactive salespeople (``is_active=False``) are kept around so leads
    they previously owned still resolve their advisor — historical
    accuracy beats list cleanliness. Inactive advisors are filtered out
    of the assignment dropdown, the public team page, and workspace
    lookups.
    """

    # Milestone 1 · Increment 3 — tenancy FK, NOT NULL. Auto-attached by
    # the pre_save fallback in :mod:`services.tenancy` when the caller
    # leaves it unset; explicit ``dealership=`` short-circuits the fallback.
    # Existing `slug` unique constraint preserved (tenant-scoped
    # `(dealership, slug)` unique is a later increment).
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="salespeople",
    )
    # Milestone 1 · Increment 4A — optional link to an auth User. Nullable
    # today because there are no auth users to backfill and Increment 4A
    # is schema-only. Increment 4C is the increment that requires this
    # link to be present for authenticated advisor workspace access.
    # SET_NULL on user delete preserves historical lead attribution
    # (matches the same rationale as `is_active=False` retention).
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="salesperson",
    )
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=128, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    photo_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    # JSON list, e.g. ["F-150", "Trucks", "First-time buyers"]. Manager edits
    # via Django admin. No enum — the demo seeder ships representative values.
    specialties = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]

    def __str__(self) -> str:
        suffix = "" if self.is_active else " (inactive)"
        return f"{self.name}{suffix}"


# Milestone 11 · Increment 1 (SESSION_114) — channel intake vocabulary.
# Fixed 5+1 set per MILESTONE_11_PLANNING.md §5.a Option A (user-
# confirmed at SESSION_114 open, recorded in §0.a). ``chat`` is the
# default so the historical (M1) row shape stays valid and the M11.1
# data migration backfills existing rows to ``chat`` (they all
# originated in the chat funnel — M1 is the only pre-M11 intake path).
LEAD_CHANNEL_CHAT = "chat"
LEAD_CHANNEL_WALK_IN = "walk_in"
LEAD_CHANNEL_PHONE = "phone"
LEAD_CHANNEL_LISTING_FORM = "listing_form"
LEAD_CHANNEL_REFERRAL = "referral"
LEAD_CHANNEL_OTHER = "other"

LEAD_CHANNEL_CHOICES = (
    (LEAD_CHANNEL_CHAT, "Chat"),
    (LEAD_CHANNEL_WALK_IN, "Walk-in"),
    (LEAD_CHANNEL_PHONE, "Phone"),
    (LEAD_CHANNEL_LISTING_FORM, "Listing form"),
    (LEAD_CHANNEL_REFERRAL, "Referral"),
    (LEAD_CHANNEL_OTHER, "Other"),
)


class CustomerLead(models.Model):
    URGENCY_CHOICES = [
        ("immediate", "Buying now"),
        ("this_week", "This week"),
        ("this_month", "This month"),
        ("researching", "Just researching"),
    ]

    # Milestone 1 · Increment 3 — tenancy FK, NOT NULL. Auto-attached by
    # the pre_save fallback in :mod:`services.tenancy` when the caller
    # leaves it unset; explicit ``dealership=`` short-circuits the fallback.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="customer_leads",
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    name = models.CharField(max_length=128)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    target_monthly_payment = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    down_payment = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    trade_in = models.CharField(max_length=255, blank=True)
    urgency = models.CharField(
        max_length=32, choices=URGENCY_CHOICES, blank=True, default=""
    )
    interested_vehicles = models.ManyToManyField(
        Vehicle, blank=True, related_name="leads"
    )
    credit_range = models.CharField(max_length=64, blank=True)
    conversation_summary = models.TextField(blank=True)
    recommended_next_action = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    handed_off = models.BooleanField(default=False)
    # Manager Phase 4: salesperson assignment. SET_NULL on advisor
    # delete/deactivate keeps the lead intact — but per the locked Phase 4
    # decision, we never auto-unassign on deactivation. The dropdown filters
    # inactive advisors; existing assignments stay.
    assigned_to = models.ForeignKey(
        Salesperson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    # Milestone 11 · Increment 1 (SESSION_114) — additive channel + referrer
    # extension per MILESTONE_11_PLANNING.md §1.1 + §1.6 (§5.a + §5.b + §5.f
    # confirmed as-recommended at SESSION_114 open). ``channel`` is
    # required-not-nullable with a ``chat`` default; the M11.1 data
    # migration backfills every historical row to ``chat`` (all pre-M11
    # rows originated in the chat funnel). ``referrer`` self-FK captures
    # who sent a referral lead; SET_NULL keeps referred rows intact when
    # the referrer is deleted (referral incentive payout logic is
    # deferred per §2 non-goals, so soft nulling is fine).
    channel = models.CharField(
        max_length=32,
        choices=LEAD_CHANNEL_CHOICES,
        default=LEAD_CHANNEL_CHAT,
    )
    referrer = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_leads",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.urgency or 'no urgency'})"


class DealerOnboardingProfile(models.Model):
    """SESSION_008: persistence for the /dealer-ai-onboarding manager flow.

    v0 is **one-store**: the view layer treats this as a singleton (loads
    .first(), upserts on save). Multi-tenant boundaries land with the
    Dealership entity in the assistant / agent roadmap; for now the
    constraint is enforced in code, not schema, so the migration stays
    cheap to revisit.

    Field shapes mirror the frontend onboarding page sections (dealership
    profile, manager preferences, salesperson seed, assistant behavior,
    pilot checklist). Names follow the future schema sketched in
    docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md so a future
    migration can split this into DealerAssistant / SalespersonAgent /
    StorePolicyProfile without renaming columns.
    """

    # Milestone 1 · Increment 3 — tenancy FK, NOT NULL. Auto-attached by
    # the pre_save fallback in :mod:`services.tenancy` when the caller
    # leaves it unset; explicit ``dealership=`` short-circuits the fallback.
    # OneToOne conversion (each Dealership has ≤1 onboarding profile) is
    # deferred to the increment that touches the onboarding endpoint,
    # per SESSION_037 instruction to preserve existing uniqueness
    # behavior until deliberately introduced.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="onboarding_profiles",
    )

    # Dealership profile.
    dealership_name = models.CharField(max_length=255, blank=True, default="")
    store_location = models.CharField(max_length=255, blank=True, default="")
    main_brands = models.CharField(max_length=255, blank=True, default="")
    sales_phone = models.CharField(max_length=64, blank=True, default="")
    website = models.CharField(max_length=255, blank=True, default="")
    # SESSION_021 — hosted logo URL. Falls back to the kit's static
    # asset (DEFAULT_DEALER.logoPath on the frontend) when blank.
    # CharField, not URLField, so the form can save partial drafts
    # without strict URL validation; the frontend type=url input gives
    # browser-side validation, and the consumer (`useBrand()`) just
    # passes the string through to `<img src>` which already handles
    # bad URLs via its own `onError` fallback.
    logo_url = models.CharField(max_length=512, blank=True, default="")

    # Manager preferences.
    sales_tone = models.CharField(max_length=128, blank=True, default="")
    pricing_comfort = models.CharField(max_length=128, blank=True, default="")
    appointment_preference = models.CharField(max_length=128, blank=True, default="")
    lead_handoff_style = models.CharField(max_length=128, blank=True, default="")

    # Salesperson seed profile (one salesperson captured during onboarding;
    # the full team lives in Salesperson via /dealer-ai-admin/team).
    salesperson_name = models.CharField(max_length=128, blank=True, default="")
    salesperson_role = models.CharField(max_length=128, blank=True, default="")
    salesperson_phone = models.CharField(max_length=64, blank=True, default="")
    salesperson_email = models.CharField(max_length=255, blank=True, default="")
    salesperson_specialties = models.CharField(max_length=512, blank=True, default="")
    salesperson_preferred_tone = models.CharField(max_length=128, blank=True, default="")
    salesperson_intro = models.TextField(blank=True, default="")

    # Assistant behavior.
    dealership_greeting = models.TextField(blank=True, default="")
    approved_phrases = models.TextField(blank=True, default="")
    banned_phrases = models.TextField(blank=True, default="")
    escalation_rule = models.TextField(blank=True, default="")
    payment_disclaimer = models.TextField(blank=True, default="")

    # Pilot checklist booleans.
    inventory_connected = models.BooleanField(default=False)
    finance_rules_reviewed = models.BooleanField(default=False)
    salespeople_added = models.BooleanField(default=False)
    demo_prompts_tested = models.BooleanField(default=False)
    pilot_approved = models.BooleanField(default=False)

    # Indie shape-of-business (SESSION_032). Persists the seven fields
    # exposed by services/dealer_config.DealerProfile so a real dealer
    # can customize them via the Setup UI instead of relying on env
    # overrides + Copper Canyon hardcoded defaults. Resolution order
    # for each field: DB value (when non-empty for strings, or `False`
    # for the bool via `bhph_configured` sentinel) → env override
    # (dealer_type only) → Copper Canyon default in
    # services/dealer_config._COPPER_CANYON_DEFAULTS.
    #
    # `dealer_type` blank = "unset, resolver falls back to env/default".
    # `bhph_configured` is a separate flag so we can distinguish "user
    # explicitly saved this profile" from "form never touched" for the
    # bool field (matters because the resolver's DB-default of True
    # would otherwise mask a franchise dealer who wants BHPH off).
    # `subprime_lenders` and `makes_carried` store one entry per line,
    # matching the existing `approved_phrases` / `banned_phrases`
    # convention. `makes_carried` supersedes the older `main_brands`
    # field; the resolver reads `makes_carried` first and falls back
    # to `main_brands` for legacy profiles.
    DEALER_TYPE_CHOICES = [
        ("independent", "Independent"),
        ("franchise", "Franchise"),
    ]
    dealer_type = models.CharField(
        max_length=20,
        choices=DEALER_TYPE_CHOICES,
        blank=True,
        default="",
    )
    bhph_enabled = models.BooleanField(default=True)
    bhph_configured = models.BooleanField(default=False)
    subprime_lenders = models.TextField(blank=True, default="")
    floor_plan_lender = models.CharField(max_length=128, blank=True, default="")
    warranty_offering = models.CharField(max_length=255, blank=True, default="")
    credit_range_served = models.CharField(max_length=255, blank=True, default="")
    makes_carried = models.TextField(blank=True, default="")

    # Milestone 2 · Increment 4a — per-tenant floor-plan APR.
    # Consumed by ``services.dealer_config.get_floor_plan_apr`` which
    # layers DB (this field) → env (``DEALER_AI_FLOOR_PLAN_APR``) →
    # Copper Canyon default (Decimal("8.5")). Nullable so the field
    # migration is additive (existing profiles keep NULL, resolver
    # falls through to env / default). Expressed in **percent units**
    # to match ``DEFAULT_APR`` in ``services/payment_engine.py`` and
    # every existing APR call site. Range validation lives in the
    # accrual engine (``daily_floor_plan_interest`` raises on
    # negative APR), NOT at the DB layer — field constraints stay
    # permissive so future operator-facing surfaces can accept
    # incrementally-entered values without validator friction.
    floor_plan_apr = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.dealership_name or "Dealer onboarding profile"


# Milestone 2 · Increment 1 — VehicleAcquisition source vocabulary.
# Kept as module-level constants so the M2.2 API + service layer, the
# M2.2 accrual command, and every test file import the canonical
# string literals without redeclaring them (mirrors the ``ROLE_*``
# pattern above). Source-of-truth: ``docs/roadmap/MILESTONE_2_PLANNING.md``
# §1.1 and ``docs/research/INVENTORY_ACQUISITION_MAPPING.md`` §2.
SOURCE_AUCTION = "auction"
SOURCE_TRADE = "trade"
SOURCE_WHOLESALE = "wholesale"
SOURCE_PRIVATE = "private"
SOURCE_OFF_LEASE = "off_lease"
SOURCE_RENTAL = "rental"
SOURCE_REPO = "repo"
SOURCE_FLEET = "fleet"

ACQUISITION_SOURCE_CHOICES = (
    (SOURCE_AUCTION, "Auction"),
    (SOURCE_TRADE, "Trade-in"),
    (SOURCE_WHOLESALE, "Wholesale (dealer-to-dealer)"),
    (SOURCE_PRIVATE, "Private party"),
    (SOURCE_OFF_LEASE, "Off-lease"),
    (SOURCE_RENTAL, "Rental return"),
    (SOURCE_REPO, "Repossession"),
    (SOURCE_FLEET, "Fleet disposal"),
)


class VehicleAcquisition(models.Model):
    """Milestone 2 · Increment 1 — per-vehicle acquisition record.

    OneToOne with :class:`Vehicle`. Captures the *buying event* — how
    the physical car arrived in inventory and every dollar that
    attached to it at acquisition time (purchase price, auction /
    broker fees, transportation, title acquisition). Post-acquisition
    costs (recon, flooring interest, admin) live on
    :class:`VehicleCost` — see the design note in
    ``docs/roadmap/MILESTONE_2_PLANNING.md`` §1.1 for why the split
    is worth having.

    Every business question Milestone 2 answers ("what have we got
    invested?", "what's the projected gross?") starts from this
    row's totals plus the sum of related ``VehicleCost`` rows.

    Note: ``Vehicle.source`` (import-provenance) and ``source`` here
    (physical-acquisition-source) are distinct concerns and must not
    collapse — see §1.1 "Leave untouched" in the planning doc.
    """

    vehicle = models.OneToOneField(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="acquisition",
    )
    # Denormalized tenancy FK. Redundant with ``vehicle.dealership`` at
    # the schema level, but keeps tenant-scoped read paths uniform
    # across every M1/M2 model and lets tenant-scoped querysets on
    # this table skip a join. ``clean()`` guards against divergence.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicle_acquisitions",
    )
    source = models.CharField(
        max_length=32,
        choices=ACQUISITION_SOURCE_CHOICES,
    )
    # Free text for "Manheim Phoenix, lane 4, run #217" or "trade
    # from CustomerLead #482" or a wholesale seller's business name.
    source_detail = models.CharField(max_length=255, blank=True, default="")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField()
    # Auction house buyer fee. Zero when the source has no fee
    # (private party, trade). Kept separate from ``purchase_price``
    # because §2.3 of ACCOUNTING_DEPARTMENT_MAPPING treats them as
    # distinct settlement lines the operator will want to see broken
    # out on the ledger UI.
    buyer_fees = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    arbitration_fees = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    transportation_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    title_acquisition_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    # Milestone 9 · Increment 1 (SESSION_100) — acquisition-buyer
    # provenance per MILESTONE_9_PLANNING.md §5.a Option A (user-
    # confirmed at SESSION_100 open). The in-house buyer who made the
    # purchase decision (auction bidder / trade appraiser / wholesale
    # negotiator). Nullable + SET_NULL so historical rows written
    # before M9.1 remain intact (no buyer provenance was captured) and
    # so a User deletion doesn't retract the acquisition record. The
    # M9.4 :func:`services.analytics.recon.buyer_estimate_accuracy`
    # verb reads this FK; a NULL row means "no provenance recorded"
    # and is excluded from the aggregation rather than treated as a
    # single anonymous buyer bucket.
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acquisitions_bought",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-purchase_date", "-created_at")
        verbose_name = "Vehicle acquisition"
        verbose_name_plural = "Vehicle acquisitions"

    def __str__(self) -> str:
        return f"Acquisition for #{self.vehicle.stock_number} ({self.get_source_display()})"

    def clean(self) -> None:
        """Guard against cross-tenant contamination at the model layer.

        The denormalized ``dealership`` FK must match the parent
        Vehicle's tenant. A view that resolves tenant from
        ``get_current_dealership(request)`` and writes an acquisition
        against a vehicle owned by a different dealership would
        silently corrupt tenant scoping. ``clean()`` raises before
        that reaches the DB.

        Data-scoping is layer 4 in ``AUTHENTICATION_MODEL.md`` §1;
        this check makes the invariant enforceable at the ORM layer
        so violations surface at the earliest possible point.
        """
        super().clean()
        # ``vehicle_id`` is required (OneToOne, not-null); access
        # ``self.vehicle`` after that check to avoid RelatedObjectDoesNotExist.
        if self.vehicle_id is None or self.dealership_id is None:
            return
        if self.vehicle.dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "VehicleAcquisition.dealership must match the parent "
                        "Vehicle's dealership. Cross-tenant contamination "
                        "guard (see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# Milestone 2 · Increment 1 — VehicleCost category vocabulary.
# ~26 categories spanning flooring, reconditioning, administrative,
# and photography — enumerated per ``VEHICLE_CENTRIC_PIVOT.md``
# §Investment ledger scope and cross-referenced against
# ``ACCOUNTING_DEPARTMENT_MAPPING.md`` §2.5–§2.10 for terminology.
# Acquisition-day costs (purchase_price, auction_fees, arbitration,
# transportation, title_acquisition) live on ``VehicleAcquisition``
# — they are NOT categories in ``VehicleCost``.
#
# Category-set groupings (FLOORING_CATEGORIES, RECON_CATEGORIES,
# ADMIN_CATEGORIES) are deliberately deferred to Milestone 2 ·
# Increment 2, where the ``services/vehicle_ledger.compute_totals``
# function first consumes them. Keeping the grouping out of M2.1
# tightens the "no business logic in the persistence layer" boundary
# the user set for this increment.

# Flooring / floor plan expenses (5).
CATEGORY_FLOOR_PLAN_INTEREST = "floor_plan_interest"
CATEGORY_FLOOR_PLAN_FEES = "floor_plan_fees"
CATEGORY_CURTAILMENT = "curtailment"
CATEGORY_WIRE_FEES = "wire_fees"
CATEGORY_BANKING_FEES = "banking_fees"

# Reconditioning expenses (13).
CATEGORY_PARTS = "parts"
CATEGORY_MECHANICAL_LABOR = "mechanical_labor"
CATEGORY_TIRES = "tires"
CATEGORY_BRAKES = "brakes"
CATEGORY_BATTERY = "battery"
CATEGORY_OIL_SERVICE = "oil_service"
CATEGORY_DIAGNOSTICS = "diagnostics"
CATEGORY_GLASS = "glass"
CATEGORY_BODY_WORK = "body_work"
CATEGORY_PAINT = "paint"
CATEGORY_UPHOLSTERY = "upholstery"
CATEGORY_WHEEL_REPAIR = "wheel_repair"
CATEGORY_DETAIL = "detail"

# Administrative expenses (7).
CATEGORY_FUEL = "fuel"
CATEGORY_LISTING_FEES = "listing_fees"
CATEGORY_ADVERTISING_ALLOCATION = "advertising_allocation"
CATEGORY_REGISTRATION = "registration"
CATEGORY_TITLE_WORK = "title_work"
CATEGORY_SHIPPING = "shipping"
CATEGORY_MISC_DEALER_EXPENSES = "misc_dealer_expenses"

# Photography (1) — separate from recon so M6 photography can
# distinguish "shot for listing" from "shot for damage doc" without
# recategorizing historical rows.
CATEGORY_PHOTOGRAPHY = "photography"

VEHICLE_COST_CATEGORY_CHOICES = (
    (CATEGORY_FLOOR_PLAN_INTEREST, "Floor plan interest"),
    (CATEGORY_FLOOR_PLAN_FEES, "Floor plan fees"),
    (CATEGORY_CURTAILMENT, "Curtailment"),
    (CATEGORY_WIRE_FEES, "Wire fees"),
    (CATEGORY_BANKING_FEES, "Banking fees"),
    (CATEGORY_PARTS, "Parts"),
    (CATEGORY_MECHANICAL_LABOR, "Mechanical labor"),
    (CATEGORY_TIRES, "Tires"),
    (CATEGORY_BRAKES, "Brakes"),
    (CATEGORY_BATTERY, "Battery"),
    (CATEGORY_OIL_SERVICE, "Oil service"),
    (CATEGORY_DIAGNOSTICS, "Diagnostics"),
    (CATEGORY_GLASS, "Glass"),
    (CATEGORY_BODY_WORK, "Body work"),
    (CATEGORY_PAINT, "Paint"),
    (CATEGORY_UPHOLSTERY, "Upholstery"),
    (CATEGORY_WHEEL_REPAIR, "Wheel repair"),
    (CATEGORY_DETAIL, "Detail"),
    (CATEGORY_FUEL, "Fuel"),
    (CATEGORY_LISTING_FEES, "Listing fees"),
    (CATEGORY_ADVERTISING_ALLOCATION, "Advertising allocation"),
    (CATEGORY_REGISTRATION, "Registration"),
    (CATEGORY_TITLE_WORK, "Title work"),
    (CATEGORY_SHIPPING, "Shipping"),
    (CATEGORY_MISC_DEALER_EXPENSES, "Miscellaneous dealer expenses"),
    (CATEGORY_PHOTOGRAPHY, "Photography"),
)

# Milestone 2 · Increment 2 — canonical category groupings.
# Deferred from Increment 1 (which shipped only the individual
# constants) because the groupings exist to serve
# ``services/vehicle_ledger.compute_totals`` — pure metadata, no
# business logic, but useful only to the service layer.
#
# Invariants (locked by ``test_vehicle_ledger.CategoryGroupings``):
#
# - Every constant in ``VEHICLE_COST_CATEGORY_CHOICES`` appears in
#   exactly one grouping (exhaustive + non-overlapping partition).
# - Photography is kept separate from administrative — VCP §Phase 5
#   photography milestone will want to distinguish "shot for
#   listing" from "shot for damage documentation" without
#   recategorizing historical rows. The ledger UI (M2.7) may
#   choose to render "Admin + photo" as a single row, but the
#   underlying partition stays granular.
FLOORING_CATEGORIES: tuple[str, ...] = (
    CATEGORY_FLOOR_PLAN_INTEREST,
    CATEGORY_FLOOR_PLAN_FEES,
    CATEGORY_CURTAILMENT,
    CATEGORY_WIRE_FEES,
    CATEGORY_BANKING_FEES,
)

RECON_CATEGORIES: tuple[str, ...] = (
    CATEGORY_PARTS,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_TIRES,
    CATEGORY_BRAKES,
    CATEGORY_BATTERY,
    CATEGORY_OIL_SERVICE,
    CATEGORY_DIAGNOSTICS,
    CATEGORY_GLASS,
    CATEGORY_BODY_WORK,
    CATEGORY_PAINT,
    CATEGORY_UPHOLSTERY,
    CATEGORY_WHEEL_REPAIR,
    CATEGORY_DETAIL,
)

ADMIN_CATEGORIES: tuple[str, ...] = (
    CATEGORY_FUEL,
    CATEGORY_LISTING_FEES,
    CATEGORY_ADVERTISING_ALLOCATION,
    CATEGORY_REGISTRATION,
    CATEGORY_TITLE_WORK,
    CATEGORY_SHIPPING,
    CATEGORY_MISC_DEALER_EXPENSES,
)

PHOTOGRAPHY_CATEGORIES: tuple[str, ...] = (
    CATEGORY_PHOTOGRAPHY,
)


class VehicleCost(models.Model):
    """Milestone 2 · Increment 1 — per-vehicle post-acquisition cost row.

    Many-per-Vehicle. Every post-acquisition expense that attaches to
    a stock number lands here: recon parts and labor, flooring
    interest (posted by the M2.2 accrual command), admin fees. The
    running total of these rows plus the parent
    :class:`VehicleAcquisition` totals equals the vehicle's current
    investment (see ``docs/roadmap/MILESTONE_2_PLANNING.md`` §1.3).

    **Negative amounts are permitted** — this is the correction
    pattern per §1.6 design note in the planning doc (mirrors
    accounting §2.11 practice). Update / delete on cost rows is not
    supported in v1; corrections happen by posting a reversing row
    whose ``reference`` points at the original.

    ``created_by`` provides authorship provenance and is nullable +
    SET_NULL so seed / management-command writes (which have no
    request-scoped user) don't require a synthetic user account.
    """

    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="costs",
    )
    # Denormalized tenancy FK — same rationale as
    # ``VehicleAcquisition.dealership``. ``clean()`` guards against
    # divergence from the parent Vehicle's tenant.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicle_costs",
    )
    category = models.CharField(
        max_length=32,
        choices=VEHICLE_COST_CATEGORY_CHOICES,
    )
    # Signed. Positive = expense; negative = correction/reversal.
    # Kept as Decimal to avoid float-drift in aggregation.
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # When the expense actually occurred (vendor invoice date, floor
    # plan accrual date, etc.) — distinct from ``created_at`` which
    # records when the row was posted to the ledger.
    incurred_at = models.DateTimeField()
    # Free text until Milestone 4 introduces a ``Vendor`` entity that
    # can data-migrate this column into an FK. Blank when the row
    # doesn't have a counterparty (e.g. floor plan interest posted
    # by the accrual command names the lender via ``reference``).
    vendor = models.CharField(max_length=255, blank=True, default="")
    # Invoice #, PO #, or accrual-run stamp ("ACCRUAL:2026-08-15").
    reference = models.CharField(max_length=128, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    # Separates committed spend (invoice received / paid) from
    # projected spend (estimate against a work order that hasn't
    # completed). Named in ``VEHICLE_CENTRIC_PIVOT.md`` as a required
    # distinction.
    is_estimate = models.BooleanField(default=False)
    # Provenance for who posted the cost. Nullable + SET_NULL so
    # historical rows survive user deletion (mirrors
    # ``Salesperson.user`` SET_NULL rationale in Increment 4A).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-incurred_at", "-created_at")
        verbose_name = "Vehicle cost"
        verbose_name_plural = "Vehicle costs"

    def __str__(self) -> str:
        return (
            f"{self.get_category_display()} ${self.amount} "
            f"on #{self.vehicle.stock_number}"
        )

    def clean(self) -> None:
        """Guard against cross-tenant contamination at the model layer.

        Same invariant as :meth:`VehicleAcquisition.clean` — the
        denormalized ``dealership`` FK must match the parent
        Vehicle's tenant. Prevents a mis-scoped view from writing a
        cost row against a vehicle in a different dealership.
        """
        super().clean()
        if self.vehicle_id is None or self.dealership_id is None:
            return
        if self.vehicle.dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "VehicleCost.dealership must match the parent "
                        "Vehicle's dealership. Cross-tenant contamination "
                        "guard (see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


class UserDealershipRole(models.Model):
    """Milestone 1 · Increment 4A — User↔Dealership membership + role.

    A single user may hold roles at multiple dealerships and may hold
    more than one role at a single dealership (owner + sales_manager is
    a realistic combination in an indie shop). The ``unique_together``
    constraint prevents duplicate (user, dealership, role) rows while
    permitting the many-to-many-plus-role shape.

    Increment 4A is schema-only: no view uses this table yet. Increment
    4B introduces the ``get_current_dealership(request)`` resolver that
    reads ``request.user.memberships.first().dealership``; Increments
    4C/4D introduce endpoint-level authorization that consults ``role``.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "dealership", "role"),)
        ordering = ("user", "dealership", "role")

    def __str__(self) -> str:
        return f"{self.user} @ {self.dealership} ({self.role})"


# Milestone 3 · Increment 1 — condition-report vocabulary.
# Four module-level enum sets support the three condition-report models
# (ConditionReport, ConditionFinding, ConditionFindingPhoto). Kept as
# module-level constants so the M3.2 service layer, the M3.6 API layer,
# and every test file import the canonical string literals without
# redeclaring them (mirrors the ROLE_* and VEHICLE_COST_CATEGORY_*
# patterns above). Sources of truth:
# ``docs/roadmap/MILESTONE_3_PLANNING.md`` §1.1 / §1.2 / §1.5 (field
# shapes) and ``docs/research/RECON_MAPPING.md`` §2.1 (category list),
# §2.2 (severity ladder), §2.5 (photo whitelist context).

# Report status — two values. The one-way ``draft → complete``
# transition is enforced at the M3.2 service layer; the persistence
# layer enforces only that ``completed_at`` agrees with ``status``.
CONDITION_REPORT_STATUS_DRAFT = "draft"
CONDITION_REPORT_STATUS_COMPLETE = "complete"

CONDITION_REPORT_STATUS_CHOICES = (
    (CONDITION_REPORT_STATUS_DRAFT, "Draft"),
    (CONDITION_REPORT_STATUS_COMPLETE, "Complete"),
)

# Finding severity — four values in escalation order per RECON §2.2.
CONDITION_SEVERITY_ADVISORY = "advisory"
CONDITION_SEVERITY_RECOMMENDED = "recommended"
CONDITION_SEVERITY_REQUIRED = "required"
CONDITION_SEVERITY_SAFETY = "safety"

CONDITION_SEVERITY_CHOICES = (
    (CONDITION_SEVERITY_ADVISORY, "Advisory"),
    (CONDITION_SEVERITY_RECOMMENDED, "Recommended"),
    (CONDITION_SEVERITY_REQUIRED, "Required"),
    (CONDITION_SEVERITY_SAFETY, "Safety"),
)

# Finding category — twelve values, flat (no hierarchy). Eleven sourced
# from RECON §2.1's multi-point-inspection category list plus one
# ``other`` escape hatch for real-inspection observations that don't
# fit the strong partition of mechanical reality (documentation issues,
# prior modification, aftermarket parts). Rationale in
# ``MILESTONE_3_PLANNING.md`` §1.2.
CONDITION_CATEGORY_MECHANICAL = "mechanical"
CONDITION_CATEGORY_COSMETIC = "cosmetic"
CONDITION_CATEGORY_BODY = "body"
CONDITION_CATEGORY_GLASS = "glass"
CONDITION_CATEGORY_TIRES = "tires"
CONDITION_CATEGORY_INTERIOR = "interior"
CONDITION_CATEGORY_FLUIDS = "fluids"
CONDITION_CATEGORY_ELECTRICAL = "electrical"
CONDITION_CATEGORY_SAFETY = "safety"
CONDITION_CATEGORY_ACCESSORIES = "accessories"
CONDITION_CATEGORY_MISSING = "missing"
CONDITION_CATEGORY_OTHER = "other"

CONDITION_CATEGORY_CHOICES = (
    (CONDITION_CATEGORY_MECHANICAL, "Mechanical"),
    (CONDITION_CATEGORY_COSMETIC, "Cosmetic / paint"),
    (CONDITION_CATEGORY_BODY, "Body / structural"),
    (CONDITION_CATEGORY_GLASS, "Glass"),
    (CONDITION_CATEGORY_TIRES, "Tires"),
    (CONDITION_CATEGORY_INTERIOR, "Interior"),
    (CONDITION_CATEGORY_FLUIDS, "Fluids"),
    (CONDITION_CATEGORY_ELECTRICAL, "Electrical"),
    (CONDITION_CATEGORY_SAFETY, "Safety"),
    (CONDITION_CATEGORY_ACCESSORIES, "Accessories / features present"),
    (CONDITION_CATEGORY_MISSING, "Missing items"),
    (CONDITION_CATEGORY_OTHER, "Other"),
)

# Photo content-type whitelist — four MIME values enforced at the
# model layer via ``choices=``. A complementary check runs at the
# M3.5 presigned-URL issuance view; the model-layer tuple is the
# last line of defense (see MILESTONE_3_PLANNING.md §1.5 content-
# type design note).
CONDITION_PHOTO_CONTENT_TYPE_JPEG = "image/jpeg"
CONDITION_PHOTO_CONTENT_TYPE_PNG = "image/png"
CONDITION_PHOTO_CONTENT_TYPE_HEIC = "image/heic"
CONDITION_PHOTO_CONTENT_TYPE_WEBP = "image/webp"

CONDITION_PHOTO_CONTENT_TYPE_CHOICES = (
    (CONDITION_PHOTO_CONTENT_TYPE_JPEG, "JPEG"),
    (CONDITION_PHOTO_CONTENT_TYPE_PNG, "PNG"),
    (CONDITION_PHOTO_CONTENT_TYPE_HEIC, "HEIC"),
    (CONDITION_PHOTO_CONTENT_TYPE_WEBP, "WEBP"),
)


class ConditionReport(models.Model):
    """Milestone 3 · Increment 1 — per-inspection condition report.

    Many-per-Vehicle. Each row is one inspection event: arrival,
    post-recon QC, pre-frontline, owner walkthrough. The report is
    the durable provenance for the ``ConditionFinding`` rows hanging
    off it — who inspected, when, at what mileage, on which vehicle.

    Draft rows are freely editable at the M3.2 service layer;
    complete rows are immutable (retrospective §6 lesson 5 applied to
    inspection history). The one-way ``draft → complete`` transition
    is enforced at the service layer in M3.2. The persistence layer
    enforces only the invariant on ``completed_at``: NULL exactly
    when status is ``draft``; set exactly when status is
    ``complete``.

    ``authored_by`` records the account that entered the report;
    ``inspector_name`` records the free-text name of the person who
    physically inspected the vehicle. The two can differ (a service
    writer transcribing a paper inspection is not the mechanic who
    did the work). ``authored_by`` is nullable + SET_NULL so
    historical rows survive user deletion; ``inspector_name``
    survives verbatim as a required field so the report remains
    legally defensible.

    Source of truth: ``docs/roadmap/MILESTONE_3_PLANNING.md`` §1.1 and
    ``docs/research/RECON_MAPPING.md`` §2.4 / §2.6 / §12.1 / §12.2.
    """

    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="condition_reports",
    )
    # Denormalized tenancy FK. Same rationale as
    # ``VehicleAcquisition.dealership`` / ``VehicleCost.dealership``:
    # uniform tenant-scoped read paths, no join required.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="condition_reports",
    )
    # Provenance for who entered the report. Nullable + SET_NULL so
    # historical rows survive user deletion (mirrors
    # ``VehicleCost.created_by`` SET_NULL rationale from M2.1).
    authored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # Free-text name of the person who physically inspected the
    # vehicle. Required per RECON §2.4. Independent of
    # ``authored_by``; see class docstring for why.
    inspector_name = models.CharField(max_length=255)
    # When the physical inspection happened, not when the row was
    # written. Required per RECON §2.4.
    inspected_at = models.DateTimeField()
    # Required per RECON §2.4 (mileage at inspection is one of the
    # explicit fields on the condition-report document).
    mileage_at_inspection = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=CONDITION_REPORT_STATUS_CHOICES,
        default=CONDITION_REPORT_STATUS_DRAFT,
    )
    # Set when the M3.2 service transitions status to ``complete``.
    # NULL on draft rows; NOT NULL on complete rows. The invariant
    # is locked by :meth:`clean`.
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-inspected_at", "-created_at")
        verbose_name = "Condition report"
        verbose_name_plural = "Condition reports"

    def __str__(self) -> str:
        return (
            f"Condition report for #{self.vehicle.stock_number} "
            f"({self.get_status_display()})"
        )

    def clean(self) -> None:
        """Persistence-layer invariants.

        Two guards:

        1. Cross-tenant contamination — the denormalized
           ``dealership`` FK must match the parent Vehicle's tenant.
           Same shape as :meth:`VehicleAcquisition.clean` /
           :meth:`VehicleCost.clean`.
        2. ``completed_at`` agrees with ``status`` — NULL exactly
           when status is ``draft``; set exactly when status is
           ``complete``. The M3.2 service layer sets both fields
           in the same write; the model layer refuses inconsistent
           combinations so a direct ORM write cannot corrupt the
           report's lifecycle state.

        The one-way ``draft → complete`` transition is a service-
        layer concern (M3.2); this model does not enforce
        transition direction. It only enforces that the two fields
        agree.
        """
        super().clean()
        if self.vehicle_id is not None and self.dealership_id is not None:
            if self.vehicle.dealership_id != self.dealership_id:
                raise ValidationError(
                    {
                        "dealership": (
                            "ConditionReport.dealership must match the "
                            "parent Vehicle's dealership. Cross-tenant "
                            "contamination guard (see "
                            "AUTHENTICATION_MODEL.md §1 layer 4)."
                        )
                    }
                )
        if self.status == CONDITION_REPORT_STATUS_DRAFT and self.completed_at is not None:
            raise ValidationError(
                {
                    "completed_at": (
                        "ConditionReport.completed_at must be NULL when "
                        "status is 'draft'. The M3.2 service layer sets "
                        "completed_at atomically with the draft → "
                        "complete transition; direct writes must respect "
                        "the same invariant."
                    )
                }
            )
        if (
            self.status == CONDITION_REPORT_STATUS_COMPLETE
            and self.completed_at is None
        ):
            raise ValidationError(
                {
                    "completed_at": (
                        "ConditionReport.completed_at must be set when "
                        "status is 'complete'. The M3.2 service layer "
                        "sets completed_at atomically with the draft → "
                        "complete transition; direct writes must respect "
                        "the same invariant."
                    )
                }
            )


class ConditionFinding(models.Model):
    """Milestone 3 · Increment 1 — one defect / needed work / missing item.

    Many-per-ConditionReport. Every row is one observation made
    during the parent report's inspection. ``description`` is the
    human's own words — RECON §2.6 prohibits AI from authoring
    findings.

    ``estimated_cost`` is **documentation only** — it never posts to
    ``VehicleCost`` and never enters ``compute_totals``. The recon
    planning decision ("must-do vs. should-do vs. won't-do") has not
    been made at inspection time (RECON §3.1); posting an estimate
    cost row here would inflate
    ``VehicleCost.projected_total_investment`` with advisory
    findings the store will never spend on. Milestone 4 owns the
    findings → recon plan → work order → cost flow.

    Source of truth: ``docs/roadmap/MILESTONE_3_PLANNING.md`` §1.2
    (see the "estimated_cost design note" for the
    VehicleCost-integration non-decision) and
    ``docs/research/RECON_MAPPING.md`` §2.1 / §2.2 / §2.6.
    """

    report = models.ForeignKey(
        "ConditionReport",
        on_delete=models.CASCADE,
        related_name="findings",
    )
    # Denormalized tenancy FK — same rationale as
    # ``ConditionReport.dealership``. ``clean()`` guards against
    # divergence from ``report.vehicle.dealership``.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="condition_findings",
    )
    category = models.CharField(
        max_length=32,
        choices=CONDITION_CATEGORY_CHOICES,
    )
    severity = models.CharField(
        max_length=16,
        choices=CONDITION_SEVERITY_CHOICES,
    )
    # The human's words. Required; RECON §2.6 prohibits AI from
    # writing findings, so the description cannot be blank.
    description = models.TextField()
    # Documentation-only estimate. Nullable because not every
    # inspection includes cost estimates (RECON §2.4). Never posts
    # to ``VehicleCost`` in M3 — the seam M4 reads when
    # auto-drafting work orders. See class docstring.
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("severity", "category", "created_at")
        verbose_name = "Condition finding"
        verbose_name_plural = "Condition findings"

    def __str__(self) -> str:
        return (
            f"{self.get_severity_display()} "
            f"{self.get_category_display()} on "
            f"#{self.report.vehicle.stock_number}"
        )

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent
        Vehicle's tenant, reached via ``report.vehicle.dealership``.
        Same shape as :meth:`ConditionReport.clean` and its M2
        analogues.
        """
        super().clean()
        if self.report_id is None or self.dealership_id is None:
            return
        parent_dealership_id = getattr(self.report.vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "ConditionFinding.dealership must match the "
                        "parent Vehicle's dealership (reached via "
                        "report.vehicle). Cross-tenant contamination "
                        "guard (see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


class ConditionFindingPhoto(models.Model):
    """Milestone 3 · Increment 1 — photo metadata for a finding.

    Many-per-ConditionFinding. Photo evidence for warranty defense
    (RECON §13.1), vendor communication (RECON §2.5), and before /
    after documentation. **Metadata only** — the actual image bytes
    live in the storage backend the M3.4 storage story configures;
    this model owns only the fields that describe *which* stored
    object belongs to *which* finding.

    Public identity is :attr:`public_id` (UUID), **not**
    :attr:`storage_key`. External references — URL segments, API
    payloads, log lines, cross-milestone attachments — bind to the
    UUID so a future storage-backend rekey or a future non-finding
    parent does not force a schema rename. The storage service
    (M3.4) reads ``storage_key`` internally; nothing outside the
    storage layer treats it as an identifier. This split was
    reviewed and added at SESSION_056 (M3.1 implementation); see
    ``MILESTONE_3_PLANNING.md`` §1.5 design notes.

    Rows in this table represent **successfully attached** storage
    objects. The M3.5 presigned-upload workflow holds the
    prospective key transiently — outside the model layer — until
    the upload lands and is verified; only after verification does
    it create the row. Consequence: any row that exists points at
    a real object. No null-guards for "row exists but object
    doesn't" leak into read paths.

    Source of truth: ``docs/roadmap/MILESTONE_3_PLANNING.md`` §1.5
    and ``docs/research/RECON_MAPPING.md`` §2.5.
    """

    # Durable public identity. External references bind here; never
    # to ``storage_key``. Added at SESSION_056 per
    # ``MILESTONE_3_PLANNING.md`` §1.5 "public identity is a UUID,
    # not the storage key" design note.
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    finding = models.ForeignKey(
        "ConditionFinding",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    # Denormalized tenancy FK — reached via
    # ``finding.report.vehicle.dealership``. Same rationale as
    # ``ConditionFinding.dealership``.
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="condition_finding_photos",
    )
    # Internal storage locator — what the storage backend reads to
    # locate the object. Required + unique at the schema layer;
    # every row corresponds to a successfully attached object (see
    # class docstring). Never exposed as a public identifier; see
    # ``public_id``.
    storage_key = models.CharField(max_length=512, unique=True)
    content_type = models.CharField(
        max_length=32,
        choices=CONDITION_PHOTO_CONTENT_TYPE_CHOICES,
    )
    # Recorded on the S3 side after upload; the M3.5 workflow
    # verifies this reflects the actual object size (mitigates
    # client size lying).
    size_bytes = models.PositiveIntegerField()
    caption = models.CharField(max_length=255, blank=True, default="")
    # Provenance for who uploaded the photo. Nullable + SET_NULL so
    # historical rows survive user deletion (mirrors
    # ``ConditionReport.authored_by`` SET_NULL rationale).
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        verbose_name = "Condition finding photo"
        verbose_name_plural = "Condition finding photos"

    def __str__(self) -> str:
        return f"Photo {self.public_id} on finding #{self.finding_id}"

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent
        Vehicle's tenant, reached via
        ``finding.report.vehicle.dealership``. Same shape as
        :meth:`ConditionFinding.clean`.
        """
        super().clean()
        if self.finding_id is None or self.dealership_id is None:
            return
        report = getattr(self.finding, "report", None)
        if report is None:
            return
        vehicle = getattr(report, "vehicle", None)
        if vehicle is None:
            return
        parent_dealership_id = getattr(vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "ConditionFindingPhoto.dealership must match "
                        "the parent Vehicle's dealership (reached via "
                        "finding.report.vehicle). Cross-tenant "
                        "contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ============================================================================
# Milestone 4 · Increment 1 (SESSION_066) — Recon persistence layer.
# ============================================================================
#
# Six new models: Vendor, ReconDecision, WorkOrder, WorkOrderFinding,
# WorkOrderPart, VendorCommunication. Persistence layer only — services,
# state transitions, ledger integration, safety scrubs, endpoints, and
# frontend all land in M4.2 → M4.7 per ``MILESTONE_4_PLANNING.md`` §7.
#
# Source of truth: ``MILESTONE_4_PLANNING.md`` §1.1 – §1.6 (field shapes),
# §3 (model-layer invariants), §5.b (Vendor deletion contract), §5.c
# (state enum), §5.d (part source enum), §5.e (ledger reference-key
# vocabulary, consumed in M4.3), and ``docs/research/RECON_MAPPING.md``
# §§3–7 + §14.
#
# Three planning refinements adopted at SESSION_066 before this code
# landed and shape the model contracts below:
#
#   1. Vendor PROTECT contract — WorkOrder.vendor and
#      VendorCommunication.vendor use ``on_delete=PROTECT``. Normal
#      removal path is ``Vendor.is_active=False``. See §1.2 / §1.3 /
#      §1.6 / §3 / §5.b.
#   2. Estimate retirement on completion — completion posts an atomic
#      reversal for the outstanding estimate plus the actual, so
#      ``projected_total_investment`` no longer double-counts completed
#      work. Persistence layer captures the field surface;
#      implementation lands in M4.3 per §5.e + §7 M4.3 sequencing.
#   3. VendorCommunication ``logged`` semantics distinct from
#      ``sent`` — ``logged`` needs a human actor + timestamp +
#      recorded body, but does not require a prior approval step.
#      ``sent`` still requires draft → approved → sent with
#      approved_by + sent_by + sent_at + nonblank sent_content.

# ----------------------------------------------------------------------------
# ReconDecision tier vocabulary — three values per RECON §3.1.
# ----------------------------------------------------------------------------

RECON_DECISION_TIER_MUST_DO = "must_do"
RECON_DECISION_TIER_SHOULD_DO = "should_do"
RECON_DECISION_TIER_WONT_DO = "wont_do"

RECON_DECISION_TIER_CHOICES = (
    (RECON_DECISION_TIER_MUST_DO, "Must do"),
    (RECON_DECISION_TIER_SHOULD_DO, "Should do"),
    (RECON_DECISION_TIER_WONT_DO, "Won't do"),
)

# ----------------------------------------------------------------------------
# WorkOrder status + venue vocabularies — five + two values per §5.c.
# ``waiting_parts`` and ``scheduled`` are deliberately NOT statuses — the
# planning §5.c "rejected additions" note explains why.
# ----------------------------------------------------------------------------

WORK_ORDER_STATUS_DRAFT = "draft"
WORK_ORDER_STATUS_APPROVED = "approved"
WORK_ORDER_STATUS_IN_PROGRESS = "in_progress"
WORK_ORDER_STATUS_COMPLETED = "completed"
WORK_ORDER_STATUS_CANCELLED = "cancelled"

WORK_ORDER_STATUS_CHOICES = (
    (WORK_ORDER_STATUS_DRAFT, "Draft"),
    (WORK_ORDER_STATUS_APPROVED, "Approved"),
    (WORK_ORDER_STATUS_IN_PROGRESS, "In progress"),
    (WORK_ORDER_STATUS_COMPLETED, "Completed"),
    (WORK_ORDER_STATUS_CANCELLED, "Cancelled"),
)

WORK_ORDER_VENUE_IN_HOUSE = "in_house"
WORK_ORDER_VENUE_OUTSOURCED = "outsourced"

WORK_ORDER_VENUE_CHOICES = (
    (WORK_ORDER_VENUE_IN_HOUSE, "In-house"),
    (WORK_ORDER_VENUE_OUTSOURCED, "Outsourced"),
)

# ----------------------------------------------------------------------------
# WorkOrderPart status + source-type vocabularies — six + seven values.
#
# Source-type finalized SESSION_066 with ``customer_supplied`` per real
# dealer operations (RECON §6.1–§6.4). ``customer_supplied`` is
# meaningfully distinct from ``in_stock`` — customer-supplied parts have
# warranty and liability implications the store did not create.
# ----------------------------------------------------------------------------

WORK_ORDER_PART_STATUS_NEEDED = "needed"
WORK_ORDER_PART_STATUS_ORDERED = "ordered"
WORK_ORDER_PART_STATUS_BACKORDERED = "backordered"
WORK_ORDER_PART_STATUS_RECEIVED = "received"
WORK_ORDER_PART_STATUS_INSTALLED = "installed"
WORK_ORDER_PART_STATUS_RETURNED = "returned"

WORK_ORDER_PART_STATUS_CHOICES = (
    (WORK_ORDER_PART_STATUS_NEEDED, "Needed"),
    (WORK_ORDER_PART_STATUS_ORDERED, "Ordered"),
    (WORK_ORDER_PART_STATUS_BACKORDERED, "Backordered"),
    (WORK_ORDER_PART_STATUS_RECEIVED, "Received"),
    (WORK_ORDER_PART_STATUS_INSTALLED, "Installed"),
    (WORK_ORDER_PART_STATUS_RETURNED, "Returned"),
)

WORK_ORDER_PART_SOURCE_OEM_DEALER = "oem_dealer"
WORK_ORDER_PART_SOURCE_LOCAL_PARTS = "local_parts"
WORK_ORDER_PART_SOURCE_ONLINE = "online"
WORK_ORDER_PART_SOURCE_SALVAGE = "salvage"
WORK_ORDER_PART_SOURCE_IN_STOCK = "in_stock"
WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED = "customer_supplied"
WORK_ORDER_PART_SOURCE_OTHER = "other"

WORK_ORDER_PART_SOURCE_TYPE_CHOICES = (
    (WORK_ORDER_PART_SOURCE_OEM_DEALER, "OEM dealer counter"),
    (WORK_ORDER_PART_SOURCE_LOCAL_PARTS, "Local parts store"),
    (WORK_ORDER_PART_SOURCE_ONLINE, "Online"),
    (WORK_ORDER_PART_SOURCE_SALVAGE, "Salvage / recycled"),
    (WORK_ORDER_PART_SOURCE_IN_STOCK, "In-house stock"),
    (WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED, "Customer supplied"),
    (WORK_ORDER_PART_SOURCE_OTHER, "Other"),
)

# ----------------------------------------------------------------------------
# VendorCommunication vocabularies — kind, channel, direction, status.
#
# ``status`` vocabulary is four values (draft / approved / sent / logged).
# The planning artifact's earlier ``failed`` value is not shipped in M4.1
# — retry / bounce handling is deferred to the prod-readiness pass per
# §5.i / §5.j. If M4.5 or the prod pass introduces send failures, the
# enum can be extended additively without breaking existing rows.
# ----------------------------------------------------------------------------

VENDOR_COMMUNICATION_KIND_VENDOR_COMM = "vendor_comm"
VENDOR_COMMUNICATION_KIND_PARTS_ORDER = "parts_order"
VENDOR_COMMUNICATION_KIND_NARRATIVE = "narrative"

VENDOR_COMMUNICATION_KIND_CHOICES = (
    (VENDOR_COMMUNICATION_KIND_VENDOR_COMM, "Vendor communication"),
    (VENDOR_COMMUNICATION_KIND_PARTS_ORDER, "Parts order"),
    (VENDOR_COMMUNICATION_KIND_NARRATIVE, "Narrative note"),
)

VENDOR_COMMUNICATION_CHANNEL_EMAIL = "email"
VENDOR_COMMUNICATION_CHANNEL_SMS = "sms"
VENDOR_COMMUNICATION_CHANNEL_PHONE = "phone"
VENDOR_COMMUNICATION_CHANNEL_IN_PERSON = "in_person"
VENDOR_COMMUNICATION_CHANNEL_INTERNAL_NOTE = "internal_note"

VENDOR_COMMUNICATION_CHANNEL_CHOICES = (
    (VENDOR_COMMUNICATION_CHANNEL_EMAIL, "Email"),
    (VENDOR_COMMUNICATION_CHANNEL_SMS, "SMS"),
    (VENDOR_COMMUNICATION_CHANNEL_PHONE, "Phone"),
    (VENDOR_COMMUNICATION_CHANNEL_IN_PERSON, "In person"),
    (VENDOR_COMMUNICATION_CHANNEL_INTERNAL_NOTE, "Internal note"),
)

VENDOR_COMMUNICATION_DIRECTION_OUTBOUND = "outbound"
VENDOR_COMMUNICATION_DIRECTION_INBOUND = "inbound"

VENDOR_COMMUNICATION_DIRECTION_CHOICES = (
    (VENDOR_COMMUNICATION_DIRECTION_OUTBOUND, "Outbound"),
    (VENDOR_COMMUNICATION_DIRECTION_INBOUND, "Inbound"),
)

VENDOR_COMMUNICATION_STATUS_DRAFT = "draft"
VENDOR_COMMUNICATION_STATUS_APPROVED = "approved"
VENDOR_COMMUNICATION_STATUS_SENT = "sent"
VENDOR_COMMUNICATION_STATUS_LOGGED = "logged"

VENDOR_COMMUNICATION_STATUS_CHOICES = (
    (VENDOR_COMMUNICATION_STATUS_DRAFT, "Draft"),
    (VENDOR_COMMUNICATION_STATUS_APPROVED, "Approved"),
    (VENDOR_COMMUNICATION_STATUS_SENT, "Sent"),
    (VENDOR_COMMUNICATION_STATUS_LOGGED, "Logged"),
)


class Vendor(models.Model):
    """Milestone 4 · Increment 1 — outsourced-work vendor.

    Many-per-Dealership. Represents a paint shop, body shop, mechanic,
    glass tech, detailer, upholstery vendor, etc. — anyone the
    dealership pays to perform recon work off-site. In-house work
    does not need a Vendor row (``WorkOrder.venue = 'in_house'``
    permits ``vendor=NULL``).

    Deletion contract (planning refinement adopted SESSION_066):

    - Normal removal path: ``Vendor.is_active = False``. Historical
      references remain intact.
    - Hard delete is **prevented at the schema layer** by
      ``on_delete=PROTECT`` on every FK that points at Vendor
      (``WorkOrder.vendor``, ``VendorCommunication.vendor``). Postgres
      / SQLite raise ``ProtectedError`` when a delete is attempted
      against a referenced Vendor row.
    - Rename is permitted and does not rewrite the free-text vendor
      snapshot on historical ``VehicleCost`` rows (M2 immutability
      preserved; see planning §5.b Option C).
    - An unreferenced Vendor may be deleted through Django or admin
      when project conventions permit; the M4.1 admin surface does not
      offer a delete button, matching the read-mostly discipline of
      the M2/M3 admins.

    ``categories`` is a JSONField list of category slugs matching the
    twelve-value ``CONDITION_CATEGORY_CHOICES`` vocabulary (e.g.
    ``["mechanical", "electrical"]`` for a full-service mechanic,
    ``["body", "cosmetic", "paint"]`` for a body shop). Persistence
    layer does not validate the list contents against
    ``CONDITION_CATEGORY_CHOICES`` — that validation belongs at the
    service / admin layer in M4.2 / M4.6, where the vocabulary can be
    surfaced as a multi-select in the UI. Storing free-form category
    slugs at the persistence layer avoids requiring a data migration
    every time the twelve-category vocabulary evolves.

    Source of truth: ``docs/roadmap/MILESTONE_4_PLANNING.md`` §1.2 and
    ``docs/research/RECON_MAPPING.md`` §5.1 / §5.2 / §5.6.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vendors",
    )
    name = models.CharField(max_length=255)
    # URL-friendly identifier scoped per-dealership. Not globally
    # unique — two independent dealerships may both work with a
    # generically-named vendor. Unique-per-dealership enforced by
    # ``Meta.constraints`` below.
    slug = models.SlugField(max_length=64)
    # List of canonical category slugs. See class docstring for why
    # persistence layer does not validate list contents.
    categories = models.JSONField(default=list, blank=True)
    phone = models.CharField(max_length=64, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        constraints = [
            models.UniqueConstraint(
                fields=("dealership", "slug"),
                name="uniq_vendor_slug_per_dealership",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ReconDecision(models.Model):
    """Milestone 4 · Increment 1 — one recon decision per finding.

    OneToOne with :class:`ConditionFinding`. Encodes the three-tier
    planning decision (must-do / should-do / won't-do) the recon
    manager applies to each finding after inspection completes. See
    RECON §3.1 for the framework rationale and §13.1 for the warranty
    exposure that motivates recording who decided a "won't do" and
    when.

    **Persistence layer does not enforce "report must be complete."**
    Per the SESSION_066 brief, that gating belongs at the M4.2
    service layer (``services/recon.py::record_decision``) — the
    model layer would need to eagerly walk
    ``finding.report.status`` on every save and would double-charge
    the guard the service already owns. The tenant-chain
    cross-tenant guard below is model-layer because the model can
    detect it via a single FK lookup without policy coupling.

    ``decided_by`` is nullable + SET_NULL so historical decisions
    survive user deletion. ``decided_at`` is not auto-set — the M4.2
    service layer stamps it when the decision is recorded. Direct
    ORM writes must supply the value.

    Source of truth: ``MILESTONE_4_PLANNING.md`` §1.1 and RECON
    §3.1 + §13.1.
    """

    finding = models.OneToOneField(
        "ConditionFinding",
        on_delete=models.CASCADE,
        related_name="recon_decision",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="recon_decisions",
    )
    tier = models.CharField(
        max_length=16,
        choices=RECON_DECISION_TIER_CHOICES,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decided_at = models.DateTimeField()
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-decided_at", "-created_at")
        verbose_name = "Recon decision"
        verbose_name_plural = "Recon decisions"

    def __str__(self) -> str:
        return (
            f"{self.get_tier_display()} decision on finding "
            f"#{self.finding_id}"
        )

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent
        Vehicle's tenant, reached via ``finding.report.vehicle``.
        Mirrors :meth:`ConditionFinding.clean`.
        """
        super().clean()
        if self.finding_id is None or self.dealership_id is None:
            return
        report = getattr(self.finding, "report", None)
        if report is None:
            return
        vehicle = getattr(report, "vehicle", None)
        if vehicle is None:
            return
        parent_dealership_id = getattr(vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "ReconDecision.dealership must match the parent "
                        "Vehicle's dealership (reached via "
                        "finding.report.vehicle). Cross-tenant "
                        "contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


class WorkOrder(models.Model):
    """Milestone 4 · Increment 1 — one recon job on one vehicle.

    Many-per-Vehicle. Represents a single unit of work (paint the
    rear quarter panel, mount tires, diagnose the transmission
    codes). May address one finding or many (see
    :class:`WorkOrderFinding` through table). May be performed
    in-house or outsourced to a :class:`Vendor`.

    ``category`` reuses ``CONDITION_CATEGORY_CHOICES`` (the twelve
    values shipped in M3.1) as the single source of truth. Per the
    SESSION_066 brief, the category vocabulary must NOT be duplicated
    into a second independently-maintained tuple — a work order
    addresses findings, and finding categories are the shared
    vocabulary.

    Persistence-layer invariants (locked at :meth:`clean`):

    - ``dealership`` matches the parent Vehicle's tenant
      (cross-tenant guard).
    - ``venue == "outsourced"`` implies ``vendor IS NOT NULL``. The
      converse is not enforced — in-house may set a vendor if the
      operator wants to record a supply relationship, though the
      M4.6 UI will typically leave it blank.
    - ``vendor.dealership`` matches ``self.dealership`` when a
      vendor is set.

    State transitions live in the M4.2 service layer
    (:mod:`services.recon`). The persistence layer accepts any
    ``status`` in ``WORK_ORDER_STATUS_CHOICES`` — service-layer
    validation refuses illegal transitions. Provenance fields
    (``approved_at`` / ``approved_by`` / ``started_at`` /
    ``started_by`` / ``completed_at`` / ``completed_by`` /
    ``cancelled_at`` / ``cancelled_by``) remain nullable at the
    persistence stage and are populated by the service on the
    corresponding transition.

    Vendor FK uses ``on_delete=PROTECT`` (planning refinement
    SESSION_066) — hard-deleting a referenced Vendor raises
    ``ProtectedError``. Normal removal path is
    ``Vendor.is_active=False``.

    Source of truth: ``MILESTONE_4_PLANNING.md`` §1.3 + §5.b + §5.c
    and RECON §4.2 + §4.6 + §5.1.
    """

    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    # Reuses CONDITION_CATEGORY_CHOICES per SESSION_066 brief — do not
    # duplicate the twelve-value vocabulary. When a work order spans
    # multiple categories, operator picks the dominant one; the
    # through-model records the actual finding→WO mapping.
    category = models.CharField(
        max_length=32,
        choices=CONDITION_CATEGORY_CHOICES,
    )
    venue = models.CharField(
        max_length=16,
        choices=WORK_ORDER_VENUE_CHOICES,
    )
    # PROTECT — a referenced vendor cannot be hard-deleted. See class
    # docstring. Nullable because ``venue='in_house'`` does not
    # require a vendor.
    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="work_orders",
    )
    # In-house technician (for venue=in_house). SET_NULL so historical
    # rows survive user deletion; unassigned is legitimate on newly
    # created work orders.
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(
        max_length=16,
        choices=WORK_ORDER_STATUS_CHOICES,
        default=WORK_ORDER_STATUS_DRAFT,
    )
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    authorized_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    actual_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    estimated_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    # Provenance for state transitions. Populated by the M4.2 service
    # layer atomically with the status transition. All nullable at
    # the persistence stage — a freshly created draft has none of
    # these set.
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    cancellation_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Work order"
        verbose_name_plural = "Work orders"

    def __str__(self) -> str:
        return (
            f"{self.get_category_display()} WO on "
            f"#{self.vehicle.stock_number} ({self.get_status_display()})"
        )

    def clean(self) -> None:
        """Structural persistence-layer invariants.

        Four guards, all model-appropriate (no policy coupling):

        1. Cross-tenant contamination — ``dealership`` matches
           ``vehicle.dealership``. Same shape as M2/M3 models.
        2. Outsourced venue requires a Vendor — ``venue='outsourced'``
           without ``vendor`` is nonsensical: outsourced work has to
           go somewhere. Failure to satisfy this at model layer is a
           bug in the M4.2 service; the guard prevents corruption
           from a direct ORM misuse.
        3. Vendor tenancy — when ``vendor`` is set, its dealership
           must match ``self.dealership``. Prevents a mis-scoped
           write from binding a work order to a vendor at another
           dealership.
        4. In-house venue MUST NOT silently require a vendor —
           explicit design invariant from the SESSION_066 brief.
           The guard is captured by leaving ``vendor`` optional; no
           positive check needed here (this note documents the
           deliberate absence of an ``in_house implies vendor IS
           NULL`` guard so a future edit does not add one).

        State-transition validation is NOT enforced here — that is
        the M4.2 service layer's job.
        """
        super().clean()
        if self.vehicle_id is not None and self.dealership_id is not None:
            if self.vehicle.dealership_id != self.dealership_id:
                raise ValidationError(
                    {
                        "dealership": (
                            "WorkOrder.dealership must match the parent "
                            "Vehicle's dealership. Cross-tenant "
                            "contamination guard (see "
                            "AUTHENTICATION_MODEL.md §1 layer 4)."
                        )
                    }
                )
        if self.venue == WORK_ORDER_VENUE_OUTSOURCED and self.vendor_id is None:
            raise ValidationError(
                {
                    "vendor": (
                        "WorkOrder with venue='outsourced' must set a "
                        "Vendor. Outsourced work has to go somewhere "
                        "— see MILESTONE_4_PLANNING.md §1.3."
                    )
                }
            )
        if self.vendor_id is not None and self.dealership_id is not None:
            vendor_dealership_id = getattr(self.vendor, "dealership_id", None)
            if (
                vendor_dealership_id is not None
                and vendor_dealership_id != self.dealership_id
            ):
                raise ValidationError(
                    {
                        "vendor": (
                            "WorkOrder.vendor must belong to the same "
                            "dealership as the work order itself. "
                            "Cross-tenant contamination guard."
                        )
                    }
                )


class WorkOrderFinding(models.Model):
    """Milestone 4 · Increment 1 — through model linking WOs to findings.

    Many-to-many between :class:`WorkOrder` and
    :class:`ConditionFinding`. Same finding may be addressed by
    multiple work orders (parts-order WO + install WO), and one work
    order may address multiple findings (a paint job that covers
    three separate cosmetic findings on the same trip to the body
    shop — RECON §3.7).

    Persistence layer invariants (locked at :meth:`clean`):

    - ``dealership`` matches ``work_order.dealership``.
    - ``dealership`` matches ``finding.report.vehicle.dealership``.
    - ``work_order.vehicle_id == finding.report.vehicle_id`` — a
      work order on Vehicle A cannot address a finding from a
      report on Vehicle B, even within the same dealership.
    - Unique together on (``work_order``, ``finding``) — a finding
      cannot be linked to the same work order twice.

    ``draft-only attach/detach`` — the "you can only edit the link
    set while the WO is a draft" workflow rule belongs at the M4.2
    service layer, not here. The through model is a pure structural
    link.

    Source of truth: ``MILESTONE_4_PLANNING.md`` §1.4 + §5.d.
    """

    work_order = models.ForeignKey(
        "WorkOrder",
        on_delete=models.CASCADE,
        related_name="finding_links",
    )
    finding = models.ForeignKey(
        "ConditionFinding",
        on_delete=models.CASCADE,
        related_name="work_order_links",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="work_order_findings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Work order → finding link"
        verbose_name_plural = "Work order → finding links"
        constraints = [
            models.UniqueConstraint(
                fields=("work_order", "finding"),
                name="uniq_workorder_finding_pair",
            ),
        ]

    def __str__(self) -> str:
        return f"WO #{self.work_order_id} → finding #{self.finding_id}"

    def clean(self) -> None:
        """Structural persistence-layer invariants.

        Three guards:

        1. ``dealership`` matches ``work_order.dealership``.
        2. ``dealership`` matches
           ``finding.report.vehicle.dealership`` — the tenant chain
           reached through the finding side.
        3. ``work_order.vehicle_id == finding.report.vehicle_id`` —
           the two sides of the link must refer to the same
           physical vehicle. Cross-vehicle links would corrupt
           traceability even within a single dealership.
        """
        super().clean()
        if self.work_order_id is not None and self.dealership_id is not None:
            wo_dealership_id = getattr(self.work_order, "dealership_id", None)
            if (
                wo_dealership_id is not None
                and wo_dealership_id != self.dealership_id
            ):
                raise ValidationError(
                    {
                        "dealership": (
                            "WorkOrderFinding.dealership must match "
                            "the parent WorkOrder's dealership. "
                            "Cross-tenant contamination guard."
                        )
                    }
                )
        if self.finding_id is not None and self.dealership_id is not None:
            report = getattr(self.finding, "report", None)
            vehicle = getattr(report, "vehicle", None) if report else None
            finding_dealership_id = (
                getattr(vehicle, "dealership_id", None) if vehicle else None
            )
            if (
                finding_dealership_id is not None
                and finding_dealership_id != self.dealership_id
            ):
                raise ValidationError(
                    {
                        "dealership": (
                            "WorkOrderFinding.dealership must match "
                            "the finding's Vehicle dealership "
                            "(reached via finding.report.vehicle). "
                            "Cross-tenant contamination guard."
                        )
                    }
                )
        if self.work_order_id is not None and self.finding_id is not None:
            wo_vehicle_id = getattr(self.work_order, "vehicle_id", None)
            report = getattr(self.finding, "report", None)
            finding_vehicle_id = getattr(report, "vehicle_id", None) if report else None
            if (
                wo_vehicle_id is not None
                and finding_vehicle_id is not None
                and wo_vehicle_id != finding_vehicle_id
            ):
                raise ValidationError(
                    {
                        "finding": (
                            "WorkOrderFinding requires the linked "
                            "WorkOrder and Finding to refer to the "
                            "same Vehicle. Cross-vehicle links are "
                            "not permitted (see "
                            "MILESTONE_4_PLANNING.md §1.4)."
                        )
                    }
                )


class WorkOrderPart(models.Model):
    """Milestone 4 · Increment 1 — one physical part needed for a WO.

    Many-per-WorkOrder. Captures the operational parts-tracking
    surface RECON §6.1–§6.6 describes: what part, from where, how
    many, at what unit cost, at what point in the ordering
    lifecycle. **Operational tracking data only** — the M4.4
    service layer owns transitions; marketplaces, auto-order, and
    payment are out of scope for the entire Milestone 4
    (planning §5.h).

    Persistence-layer invariants:

    - ``dealership`` matches ``work_order.dealership`` (which
      in turn must match ``work_order.vehicle.dealership`` per
      :meth:`WorkOrder.clean`).
    - ``quantity >= 1`` (enforced via ``MinValueValidator(1)``
      surfaced by ``full_clean``).
    - Canonical ``status`` and ``source_type`` choices.
    - ``unit_cost`` is Decimal with the M2/M3 house
      ``max_digits=10, decimal_places=2`` shape.

    Status-transition validation and timestamp population belong at
    the M4.4 service layer. The per-state timestamps
    (``ordered_at``, ``received_at``, ``installed_at``,
    ``returned_at``) remain nullable at persistence and are set by
    the corresponding service function.

    Source of truth: ``MILESTONE_4_PLANNING.md`` §1.5 + §5.h and
    RECON §3.5 + §6.1–§6.6.
    """

    work_order = models.ForeignKey(
        "WorkOrder",
        on_delete=models.CASCADE,
        related_name="parts",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="work_order_parts",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    part_number = models.CharField(max_length=128, blank=True, default="")
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=16,
        choices=WORK_ORDER_PART_STATUS_CHOICES,
        default=WORK_ORDER_PART_STATUS_NEEDED,
    )
    source_type = models.CharField(
        max_length=32,
        choices=WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
        default=WORK_ORDER_PART_SOURCE_IN_STOCK,
    )
    # Free-text vendor / store name at the parts side. No FK to
    # :class:`Vendor` because parts suppliers are a different
    # population from recon vendors (planning §1.5).
    source_name = models.CharField(max_length=255, blank=True, default="")
    ordered_at = models.DateField(null=True, blank=True)
    received_at = models.DateField(null=True, blank=True)
    installed_at = models.DateField(null=True, blank=True)
    returned_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Work order part"
        verbose_name_plural = "Work order parts"

    def __str__(self) -> str:
        return f"{self.name} (x{self.quantity}) on WO #{self.work_order_id}"

    def clean(self) -> None:
        """Cross-tenant guard.

        ``dealership`` must match the parent WorkOrder's tenant.
        Because WorkOrder itself validates
        ``dealership == vehicle.dealership``, this indirectly locks
        the tenant chain WorkOrderPart → WorkOrder → Vehicle.
        """
        super().clean()
        if self.work_order_id is not None and self.dealership_id is not None:
            wo_dealership_id = getattr(self.work_order, "dealership_id", None)
            if (
                wo_dealership_id is not None
                and wo_dealership_id != self.dealership_id
            ):
                raise ValidationError(
                    {
                        "dealership": (
                            "WorkOrderPart.dealership must match the "
                            "parent WorkOrder's dealership. Cross-tenant "
                            "contamination guard."
                        )
                    }
                )


class VendorCommunication(models.Model):
    """Milestone 4 · Increment 1 — one record of communication with a vendor.

    Many-per-WorkOrder and many-per-Vendor (nullable both). Captures
    every communication event the store makes or receives about a
    recon job: AI-drafted vendor emails, parts-order requests,
    operator-recorded phone calls, inbound status updates from a
    vendor, in-person conversations at the shop.

    **Content field convention (SESSION_066 planning refinement).**
    Two distinct workflows share this model:

    - **AI-drafted outbound (kind=vendor_comm / parts_order).**
      ``draft_content`` holds the AI-drafted body. ``draft →
      approved → sent`` is the state ladder. On ``sent``,
      ``sent_content`` captures the final sent body (which may
      differ from the draft if the operator edited before sending).
      All three status transitions require the corresponding
      actor + timestamp fields.
    - **Operator-recorded (channel=phone / in_person / inbound
      emails logged after receipt; often kind=narrative).** The
      operator creates a row directly at ``status='logged'``.
      ``draft_content`` holds the recorded body (what was said,
      what was heard). ``sent_by`` + ``sent_at`` capture the human
      actor and timestamp of the recording. **No approval step is
      required** — this is not an AI-drafted claim, it is a human
      recording an off-system communication.

    Status-invariant matrix (enforced at :meth:`clean`):

    | status     | required                                                  |
    |------------|-----------------------------------------------------------|
    | draft      | (no additional structural requirement)                    |
    | approved   | approved_by + approved_at                                 |
    | sent       | approved_by + approved_at + sent_by + sent_at + nonblank  |
    |            | sent_content                                              |
    | logged     | sent_by + sent_at + nonblank draft_content                |

    **AI-generated content may never jump directly to logged** —
    enforced at the M4.5 service layer, not at model layer (a
    persistence-only guard cannot distinguish AI-drafted from
    operator-recorded rows).

    Vendor FK uses ``on_delete=PROTECT`` (planning refinement
    SESSION_066) — hard-deleting a referenced Vendor raises
    ``ProtectedError``. Nullable because a comm row may be authored
    before the operator identifies which vendor it belongs to (e.g.
    an inbound call logged against a work order pending vendor
    assignment).

    Source of truth: ``MILESTONE_4_PLANNING.md`` §1.6 + §5.b + §5.g
    and RECON §5.6 + §14.7 + §14.8 + §16.5.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vendor_communications",
    )
    # PROTECT — cannot hard-delete a referenced Vendor. See class
    # docstring. Nullable because a comm may precede vendor
    # identification.
    vendor = models.ForeignKey(
        "Vendor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="communications",
    )
    # SET_NULL — comms can precede WO assignment; historical comms
    # about a deleted WO are retained without their WO parent.
    work_order = models.ForeignKey(
        "WorkOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communications",
    )
    kind = models.CharField(
        max_length=16,
        choices=VENDOR_COMMUNICATION_KIND_CHOICES,
    )
    channel = models.CharField(
        max_length=16,
        choices=VENDOR_COMMUNICATION_CHANNEL_CHOICES,
    )
    direction = models.CharField(
        max_length=16,
        choices=VENDOR_COMMUNICATION_DIRECTION_CHOICES,
    )
    status = models.CharField(
        max_length=16,
        choices=VENDOR_COMMUNICATION_STATUS_CHOICES,
        default=VENDOR_COMMUNICATION_STATUS_DRAFT,
    )
    # Body content. For AI-drafted rows: the initial AI draft. For
    # operator-recorded (logged) rows: the recorded body of what
    # was said / heard. See class docstring for the two-workflow
    # rationale.
    draft_content = models.TextField(blank=True, default="")
    # Final sent body — only meaningful when status='sent'. May
    # differ from draft_content if the operator edited before
    # sending.
    sent_content = models.TextField(blank=True, default="")
    # JSONField mapping sentence indices to source-bundle keys.
    # Populated by the M4.5 service; default empty dict.
    source_provenance = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")

    # Actor + timestamp provenance. Nullable at persistence; the
    # M4.5 service layer sets each pair atomically with the
    # corresponding transition. ``clean()`` enforces the
    # per-status requirement matrix.
    drafted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    drafted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Vendor communication"
        verbose_name_plural = "Vendor communications"

    def __str__(self) -> str:
        return (
            f"{self.get_kind_display()} via "
            f"{self.get_channel_display()} "
            f"({self.get_status_display()})"
        )

    def clean(self) -> None:
        """Structural persistence-layer invariants.

        Cross-tenant guards:

        - When ``vendor`` is set, ``vendor.dealership`` must match
          ``self.dealership``.
        - When ``work_order`` is set, ``work_order.dealership`` must
          match ``self.dealership``.
        - When both ``vendor`` and ``work_order`` are set, they must
          belong to the same dealership.

        Status-invariant matrix (SESSION_066 refinement — separates
        ``sent`` from ``logged``):

        - ``status='sent'`` requires nonblank ``sent_content`` +
          ``approved_by`` + ``approved_at`` + ``sent_by`` + ``sent_at``.
        - ``status='approved'`` requires ``approved_by`` +
          ``approved_at``.
        - ``status='logged'`` requires nonblank ``draft_content`` +
          ``sent_by`` + ``sent_at``. No approval step required.
        """
        super().clean()

        if self.vendor_id is not None and self.dealership_id is not None:
            vendor_dealership_id = getattr(self.vendor, "dealership_id", None)
            if (
                vendor_dealership_id is not None
                and vendor_dealership_id != self.dealership_id
            ):
                raise ValidationError(
                    {
                        "vendor": (
                            "VendorCommunication.vendor must belong to "
                            "the same dealership as the communication "
                            "itself. Cross-tenant contamination guard."
                        )
                    }
                )
        if self.work_order_id is not None and self.dealership_id is not None:
            wo_dealership_id = getattr(self.work_order, "dealership_id", None)
            if (
                wo_dealership_id is not None
                and wo_dealership_id != self.dealership_id
            ):
                raise ValidationError(
                    {
                        "work_order": (
                            "VendorCommunication.work_order must belong "
                            "to the same dealership as the communication "
                            "itself. Cross-tenant contamination guard."
                        )
                    }
                )
        if self.vendor_id is not None and self.work_order_id is not None:
            vendor_dealership_id = getattr(self.vendor, "dealership_id", None)
            wo_dealership_id = getattr(self.work_order, "dealership_id", None)
            if (
                vendor_dealership_id is not None
                and wo_dealership_id is not None
                and vendor_dealership_id != wo_dealership_id
            ):
                raise ValidationError(
                    {
                        "work_order": (
                            "VendorCommunication vendor and work_order "
                            "must belong to the same dealership when "
                            "both are set. Cross-tenant contamination "
                            "guard."
                        )
                    }
                )

        if self.status == VENDOR_COMMUNICATION_STATUS_APPROVED:
            if self.approved_by_id is None or self.approved_at is None:
                raise ValidationError(
                    {
                        "status": (
                            "VendorCommunication status='approved' "
                            "requires approved_by and approved_at."
                        )
                    }
                )
        elif self.status == VENDOR_COMMUNICATION_STATUS_SENT:
            missing = []
            if not (self.sent_content or "").strip():
                missing.append("sent_content")
            if self.approved_by_id is None:
                missing.append("approved_by")
            if self.approved_at is None:
                missing.append("approved_at")
            if self.sent_by_id is None:
                missing.append("sent_by")
            if self.sent_at is None:
                missing.append("sent_at")
            if missing:
                raise ValidationError(
                    {
                        "status": (
                            "VendorCommunication status='sent' requires "
                            f"{', '.join(missing)}."
                        )
                    }
                )
        elif self.status == VENDOR_COMMUNICATION_STATUS_LOGGED:
            missing = []
            if not (self.draft_content or "").strip():
                missing.append("draft_content (recorded body)")
            if self.sent_by_id is None:
                missing.append("sent_by (human actor)")
            if self.sent_at is None:
                missing.append("sent_at (recorded timestamp)")
            if missing:
                raise ValidationError(
                    {
                        "status": (
                            "VendorCommunication status='logged' "
                            f"requires {', '.join(missing)}. "
                            "'logged' rows do not require prior "
                            "approval — see MILESTONE_4_PLANNING.md "
                            "§1.6 (SESSION_066 refinement)."
                        )
                    }
                )


# ----------------------------------------------------------------------------
# Milestone 5 · Increment 1 (SESSION_075) — Vehicle lifecycle stage vocabulary.
#
# Twelve canonical stages per MILESTONE_5_PLANNING.md §5.a (Modified Option C).
# The retail-preparation pipeline is eight ordered stages; the operational
# categories are four unordered dispositions. Order in the tuple below matches
# the retail-preparation flow followed by the operational categories in the
# order they were resolved at SESSION_075.
#
# The ``sold`` stage is explicitly NOT SHIPPED in M5 — an enum value is a
# shipped state even if the service always rejects transitions into it, and
# shipping a state the service refuses is dishonest. M9 will add ``sold``
# alongside the ``Sale`` model when sale provenance exists.
# ----------------------------------------------------------------------------

VEHICLE_STAGE_INCOMING = "incoming"
VEHICLE_STAGE_INSPECTION = "inspection"
VEHICLE_STAGE_RECON = "recon"
VEHICLE_STAGE_QC = "qc"
VEHICLE_STAGE_DETAIL = "detail"
VEHICLE_STAGE_PHOTOGRAPHY = "photography"
VEHICLE_STAGE_LISTING = "listing"
VEHICLE_STAGE_FRONTLINE = "frontline"
VEHICLE_STAGE_WHOLESALE_OUT = "wholesale_out"
VEHICLE_STAGE_HOLD_RESERVED = "hold_reserved"
VEHICLE_STAGE_COMPANY_USE = "company_use"
VEHICLE_STAGE_OFF_MARKET = "off_market"

VEHICLE_STAGE_CHOICES = (
    (VEHICLE_STAGE_INCOMING, "Incoming"),
    (VEHICLE_STAGE_INSPECTION, "Inspection"),
    (VEHICLE_STAGE_RECON, "Recon"),
    (VEHICLE_STAGE_QC, "QC"),
    (VEHICLE_STAGE_DETAIL, "Detail"),
    (VEHICLE_STAGE_PHOTOGRAPHY, "Photography"),
    (VEHICLE_STAGE_LISTING, "Listing"),
    (VEHICLE_STAGE_FRONTLINE, "Frontline"),
    (VEHICLE_STAGE_WHOLESALE_OUT, "Wholesale out"),
    (VEHICLE_STAGE_HOLD_RESERVED, "Hold / reserved"),
    (VEHICLE_STAGE_COMPANY_USE, "Company use"),
    (VEHICLE_STAGE_OFF_MARKET, "Off market"),
)

# ----------------------------------------------------------------------------
# Milestone 5 · Increment 1 (SESSION_075) — Vehicle-stage trigger vocabulary.
#
# Four canonical trigger values per MILESTONE_5_PLANNING.md §5.b. Semantics:
#
# - ``manual`` — operator initiated (M5.4 endpoint).
# - ``rule`` — deterministic rule fired and the operator confirmed via the
#   suggested-transitions panel. Any event with ``trigger='rule'`` should
#   carry a non-blank ``rule_name``; the M5.2 service enforces this
#   invariant, not the persistence layer (see class docstrings below).
# - ``import`` — seeded from an external import (bulk upload, DMS sync).
# - ``bootstrap`` — created by ``ensure_current_stage`` (M5.2) when no row
#   exists, or by the M5.1 ``0017`` data migration. ``from_stage=None`` on
#   ``VehicleStageEvent`` is legitimate ONLY for ``trigger='bootstrap'``;
#   this too is a service-layer / migration-layer invariant, not a
#   persistence-layer one.
# ----------------------------------------------------------------------------

VEHICLE_STAGE_TRIGGER_MANUAL = "manual"
VEHICLE_STAGE_TRIGGER_RULE = "rule"
VEHICLE_STAGE_TRIGGER_IMPORT = "import"
VEHICLE_STAGE_TRIGGER_BOOTSTRAP = "bootstrap"

VEHICLE_STAGE_TRIGGER_CHOICES = (
    (VEHICLE_STAGE_TRIGGER_MANUAL, "Manual"),
    (VEHICLE_STAGE_TRIGGER_RULE, "Rule"),
    (VEHICLE_STAGE_TRIGGER_IMPORT, "Import"),
    (VEHICLE_STAGE_TRIGGER_BOOTSTRAP, "Bootstrap"),
)


class VehicleStage(models.Model):
    """Milestone 5 · Increment 1 — current lifecycle stage for one Vehicle.

    OneToOne with :class:`Vehicle`. Records the vehicle's current lifecycle
    stage and the provenance of the last transition (who, when, and what
    trigger). The full audit trail lives on :class:`VehicleStageEvent`.

    **Persistence layer is neutral about transitions.** The state machine
    (allowed from/to transitions, role authority, deterministic rule
    evaluation) lives in ``services/vehicle_lifecycle.py`` at M5.2. The
    persistence layer only enforces:

    1. Cross-tenant contamination — ``dealership`` matches
       ``vehicle.dealership``.
    2. Enum-membership — ``current_stage`` is one of
       :data:`VEHICLE_STAGE_CHOICES` values; ``trigger`` is one of
       :data:`VEHICLE_STAGE_TRIGGER_CHOICES` values.

    **No side effects on save.** ``VehicleStage.save()`` does NOT create a
    :class:`VehicleStageEvent` row. Event creation is an explicit,
    service-layer concern — the M5.2 ``advance_stage`` writes both rows
    atomically inside a ``transaction.atomic()`` block.

    **No auto-bootstrap on read.** Per MILESTONE_5_PLANNING.md §1.6
    (SESSION_075 refinement), ``Vehicle.current_stage`` @property (M5.2)
    delegates to a **pure** ``get_current_stage()`` helper that may return
    ``None``. The mutating side (``ensure_current_stage()``) is a distinct
    explicit verb, not a property-read side effect.

    Source of truth: ``docs/roadmap/MILESTONE_5_PLANNING.md`` §1.1 + §5.a
    + §5.c + §0.a (SESSION_075 amendments).
    """

    vehicle = models.OneToOneField(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="stage",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicle_stages",
    )
    current_stage = models.CharField(
        max_length=32,
        choices=VEHICLE_STAGE_CHOICES,
    )
    entered_at = models.DateTimeField()
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    trigger = models.CharField(
        max_length=16,
        choices=VEHICLE_STAGE_TRIGGER_CHOICES,
    )
    # The operator's reason for the last transition (populated by the M5.2
    # service on ``manual``/``rule``/``import`` transitions; blank for
    # ``bootstrap``). The full audit trail is the event log — this field is
    # a convenience for surfacing "why is the vehicle here?" in the M5.4
    # dashboard without walking events.
    last_transition_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "Vehicle stage"
        verbose_name_plural = "Vehicle stages"

    def __str__(self) -> str:
        # Cheap read — vehicle FK is required so we can dereference.
        return (
            f"{self.get_current_stage_display()} on "
            f"#{self.vehicle.stock_number}"
        )

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent Vehicle's
        tenant. Mirrors :meth:`WorkOrder.clean` / :meth:`ReconDecision.clean`
        / :meth:`VehicleAcquisition.clean`.
        """
        super().clean()
        if self.vehicle_id is None or self.dealership_id is None:
            return
        parent_dealership_id = getattr(self.vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "VehicleStage.dealership must match the parent "
                        "Vehicle's dealership. Cross-tenant "
                        "contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


class VehicleStageEvent(models.Model):
    """Milestone 5 · Increment 1 — immutable stage-transition event log.

    Many-per-Vehicle. Records every stage transition (or the initial
    bootstrap event that establishes the vehicle's starting stage). The
    event log is the durable audit trail M8 aggregates for per-stage
    aging analytics.

    **Append-only history.** Django technically permits ``.save()`` on an
    existing row; the M5.1 test suite locks the append-only contract
    behaviorally (workflow code creates only, never updates), and the M5.2
    service refuses to expose an event-update surface. Downstream code
    must NOT edit event rows.

    **``from_stage=None`` is legitimate ONLY for bootstrap events.** The
    M5.1 persistence layer permits ``from_stage=None`` on any event so
    the ``0017`` bootstrap data migration can write initial-state events
    without a synthetic ``from`` value. The invariant "every non-bootstrap
    event has ``from_stage`` set" is enforced at the M5.2 service layer —
    ``advance_stage`` never creates an event with ``from_stage=None``.

    **``trigger='rule'`` should carry a non-blank ``rule_name``.** Also a
    service-layer invariant (M5.2), not a persistence-layer one. A
    persistence check would need to know M5.3's rule catalog to
    distinguish a legitimate blank from a service bug.

    **No side effects on save.** Creating a ``VehicleStageEvent`` does
    NOT mutate the paired :class:`VehicleStage` current stage. The M5.2
    ``advance_stage`` updates both atomically; direct ORM writes do NOT
    trigger a cascade.

    Source of truth: ``MILESTONE_5_PLANNING.md`` §1.2 + §5.b + §5.c
    + §0.a (SESSION_075 amendments).
    """

    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="stage_events",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicle_stage_events",
    )
    # Nullable at persistence layer for the bootstrap event ONLY. Every
    # non-bootstrap event carries a from_stage; enforcement lives in the
    # M5.2 service.
    from_stage = models.CharField(
        max_length=32,
        choices=VEHICLE_STAGE_CHOICES,
        null=True,
        blank=True,
    )
    to_stage = models.CharField(
        max_length=32,
        choices=VEHICLE_STAGE_CHOICES,
    )
    entered_at = models.DateTimeField()
    # SET_NULL so historical events survive user deletion.
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    trigger = models.CharField(
        max_length=16,
        choices=VEHICLE_STAGE_TRIGGER_CHOICES,
    )
    # When trigger='rule', which specific rule fired. Non-blank enforcement
    # for rule-trigger events is a service-layer invariant (M5.2).
    rule_name = models.CharField(max_length=128, blank=True, default="")
    # Operator's reason (for manual triggers) / rule evidence summary (for
    # rule triggers) / import payload annotation (for import triggers) /
    # blank (for bootstrap).
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # -entered_at gives caller-visible reverse chronology; -created_at
        # is a deterministic tiebreaker for two events recorded with the
        # same entered_at (e.g. the bootstrap migration writes one
        # timestamp for every vehicle).
        ordering = ("-entered_at", "-created_at")
        verbose_name = "Vehicle stage event"
        verbose_name_plural = "Vehicle stage events"

    def __str__(self) -> str:
        from_label = self.get_from_stage_display() if self.from_stage else "∅"
        return (
            f"#{self.vehicle_id}: {from_label} → "
            f"{self.get_to_stage_display()} ({self.get_trigger_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent Vehicle's
        tenant. Mirrors :meth:`VehicleStage.clean`.
        """
        super().clean()
        if self.vehicle_id is None or self.dealership_id is None:
            return
        parent_dealership_id = getattr(self.vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "VehicleStageEvent.dealership must match the "
                        "parent Vehicle's dealership. Cross-tenant "
                        "contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ----------------------------------------------------------------------------
# Milestone 6 · Increment 1 (SESSION_082) — VehiclePhoto content-type vocabulary.
#
# Three canonical MIME values for photo gallery uploads per
# MILESTONE_6_PLANNING.md §1.1. Deliberately narrower than the M3.1
# ``CONDITION_PHOTO_CONTENT_TYPE_CHOICES`` set (which includes HEIC):
# vehicle photos are marketing / listing content that will be served to
# customers via the M6.5 showroom endpoint, and HEIC has poor
# cross-browser support. Operators upload JPEG / PNG / WebP.
#
# The M6.2 photo storage layer (extending ``services/photo_storage.py``
# per §5.c Option A) re-validates against this whitelist at the
# presigned-URL boundary, mirroring the M3.4 defense-in-depth posture.
# ----------------------------------------------------------------------------

VEHICLE_PHOTO_CONTENT_TYPE_JPEG = "image/jpeg"
VEHICLE_PHOTO_CONTENT_TYPE_PNG = "image/png"
VEHICLE_PHOTO_CONTENT_TYPE_WEBP = "image/webp"

VEHICLE_PHOTO_CONTENT_TYPE_CHOICES = (
    (VEHICLE_PHOTO_CONTENT_TYPE_JPEG, "JPEG"),
    (VEHICLE_PHOTO_CONTENT_TYPE_PNG, "PNG"),
    (VEHICLE_PHOTO_CONTENT_TYPE_WEBP, "WebP"),
)


# ----------------------------------------------------------------------------
# Milestone 6 · Increment 1 (SESSION_082) — VehicleListing status vocabulary.
#
# Four canonical status values per MILESTONE_6_PLANNING.md §5.a Option A
# (user-confirmed at SESSION_082 open):
#
# - ``draft`` — AI has drafted the listing body; awaiting operator approval.
# - ``approved`` — Operator has approved the draft; awaiting publish gesture.
# - ``published`` — Visible on the M6.5 ``/showroom`` endpoint. Drives the
#   M6.4 ``_rule_listing_to_frontline`` predicate.
# - ``unpublished`` — Withdrawn from customer view. Distinct from ``draft``
#   because the listing existed as published copy at some point.
#
# The state machine (allowed status transitions, actor-role authority)
# lives in the M6.3 ``services/vehicle_listing.py`` module. The
# persistence layer enforces only enum-membership (via ``choices=``) and
# cross-tenant contamination (via ``clean()``). Mirrors the M5.1
# discipline: transitions belong to services, not to persistence.
# ----------------------------------------------------------------------------

VEHICLE_LISTING_STATUS_DRAFT = "draft"
VEHICLE_LISTING_STATUS_APPROVED = "approved"
VEHICLE_LISTING_STATUS_PUBLISHED = "published"
VEHICLE_LISTING_STATUS_UNPUBLISHED = "unpublished"

VEHICLE_LISTING_STATUS_CHOICES = (
    (VEHICLE_LISTING_STATUS_DRAFT, "Draft"),
    (VEHICLE_LISTING_STATUS_APPROVED, "Approved"),
    (VEHICLE_LISTING_STATUS_PUBLISHED, "Published"),
    (VEHICLE_LISTING_STATUS_UNPUBLISHED, "Unpublished"),
)


class VehiclePhoto(models.Model):
    """Milestone 6 · Increment 1 — photo metadata for a vehicle gallery.

    Many-per-Vehicle. Metadata only — the actual image bytes live in the
    storage backend the M6.2 photo storage extension configures (per
    ``MILESTONE_6_PLANNING.md`` §5.c Option A — extends the M3.4
    ``services/photo_storage.py`` primitive with a
    ``store_vehicle_photo(...)`` verb). This model owns only the fields
    that describe *which* stored object belongs to *which* vehicle.

    **Persistence layer is neutral about workflow.** The M6.2 photo
    gallery service (``upload_photo``, ``set_primary``, ``reorder``,
    ``mark_deleted``, ``restore_deleted``, ``listing_ready_count`` per
    §1.4) owns every mutation invariant. The persistence layer enforces
    only:

    1. Cross-tenant contamination — ``dealership`` matches
       ``vehicle.dealership``.
    2. Enum-membership — ``content_type`` is one of
       :data:`VEHICLE_PHOTO_CONTENT_TYPE_CHOICES` values.

    **Safer-direction deletion (M6 §7 lesson 7).** The operator delete
    gesture at the M6.2 service layer sets ``marked_deleted_at`` and
    ``deleted_by`` rather than removing the row. A future physical-delete
    reaper (deferred to M6.2+) processes the tombstoned rows. Consumers
    that surface photos to customers filter ``marked_deleted_at=None``.

    **``is_primary`` uniqueness is a service-layer invariant.** The M6.2
    ``set_primary`` service atomically flips the previous primary to
    False and the new primary to True inside a single transaction. Per
    §1.1, no DB uniqueness constraint — a constraint would force the
    operator's "swap primary" gesture into a two-step delete-then-insert
    dance. Direct ORM writes bypassing the service can produce multiple
    primary rows; the service is the enforcement layer.

    **Listing-ready predicate.** The M6.4 rule
    ``_rule_photography_to_listing`` computes readiness from
    ``width_px`` + ``height_px`` at query time (planning §1.7). No
    stored boolean — a boolean would risk drift from the actual
    dimensions if a future re-processing step altered the underlying
    object. Predicate lives in the M6.4 service.

    Source of truth: ``docs/roadmap/MILESTONE_6_PLANNING.md`` §1.1 +
    §5.a-§5.c (§5.a irrelevant to photo; §5.b + §5.c apply to M6.4 /
    M6.2 respectively). ``public_id`` added at SESSION_083 M6.2 per
    §2 Option A (user-confirmed) — durable external identifier
    mirroring the M3.1 ``ConditionFindingPhoto.public_id`` pattern so
    the M6.5 admin API has a tenant-safe reference that isn't an
    enumerable integer PK.
    """

    # Durable public identity. External references bind here; never to
    # ``storage_key`` (internal to the storage layer). Mirrors the M3.1
    # ``ConditionFindingPhoto.public_id`` pattern. Added at SESSION_083
    # M6.2 per §2 Option A. The M6.2 upload service seeds this from a
    # fresh ``uuid.uuid4()`` that is also embedded in the canonical
    # ``storage_key``, so the UUID and the storage key stay bound
    # even if the storage layer is later rekeyed.
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicle_photos",
    )
    # Storage-backend key produced by the M6.2 extension of
    # ``services/photo_storage.py``. Unique — every row corresponds to a
    # distinct stored object. Never exposed as an external identifier;
    # external code binds to ``public_id`` (UUID) instead.
    storage_key = models.CharField(max_length=512, unique=True)
    content_type = models.CharField(
        max_length=32,
        choices=VEHICLE_PHOTO_CONTENT_TYPE_CHOICES,
    )
    # Pixel dimensions captured at upload time. Positive by construction
    # — a zero-dimension image is not a legitimate photo. Drives the
    # M6.4 ``_rule_photography_to_listing`` listing-ready predicate
    # (per planning §1.7).
    width_px = models.PositiveIntegerField()
    height_px = models.PositiveIntegerField()
    # Operator-controlled ordering. Integer (not positive) so operators
    # can push a photo "to the top" by assigning a negative sort_order
    # without a bulk-renumber. Ties broken by ``uploaded_at`` in
    # ``Meta.ordering``.
    sort_order = models.IntegerField(default=0)
    # One hero photo per vehicle at the service layer; violation is a
    # M6.2 service-layer refusal, not a DB uniqueness constraint. See
    # class docstring for the rationale.
    is_primary = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, default="")
    # SET_NULL so historical rows survive user deletion (mirrors
    # ``ConditionFindingPhoto.uploaded_by``).
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # Safer-direction deletion — the M6.2 delete gesture stamps
    # ``marked_deleted_at`` rather than removing the row. A future
    # physical-delete reaper (M6.2+ or later) processes the tombstones.
    marked_deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # sort_order first (operator-controlled gallery order); uploaded_at
        # as deterministic tiebreaker within a sort_order band.
        ordering = ("sort_order", "uploaded_at")
        verbose_name = "Vehicle photo"
        verbose_name_plural = "Vehicle photos"

    def __str__(self) -> str:
        primary_marker = " [primary]" if self.is_primary else ""
        deleted_marker = " [deleted]" if self.marked_deleted_at else ""
        return (
            f"Photo #{self.pk} ({self.public_id}) on "
            f"vehicle #{self.vehicle_id}{primary_marker}{deleted_marker}"
        )

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent Vehicle's
        tenant. Mirrors :meth:`VehicleStage.clean` and
        :meth:`ConditionFindingPhoto.clean`.
        """
        super().clean()
        if self.vehicle_id is None or self.dealership_id is None:
            return
        parent_dealership_id = getattr(self.vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "VehiclePhoto.dealership must match the parent "
                        "Vehicle's dealership. Cross-tenant "
                        "contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


class VehicleListing(models.Model):
    """Milestone 6 · Increment 1 — AI-drafted listing copy for one Vehicle.

    OneToOne with :class:`Vehicle`. Records the AI-drafted listing body,
    the approve/publish/unpublish audit trail, and the source-provenance
    map (mirroring the M4.5 ``VendorCommunication`` pattern).

    **Persistence layer is neutral about state transitions.** The state
    machine (allowed ``draft → approved → published → unpublished``
    transitions, role authority, publish-side effects) lives in the M6.3
    ``services/vehicle_listing.py`` module. The persistence layer
    enforces only:

    1. Cross-tenant contamination — ``dealership`` matches
       ``vehicle.dealership``.
    2. Enum-membership — ``status`` is one of
       :data:`VEHICLE_LISTING_STATUS_CHOICES` values.

    Unlike :class:`VendorCommunication`, the M6.1 persistence layer does
    NOT enforce a status-invariant matrix (nonblank body when published,
    etc.). Rationale: the M6.3 service is the single write path (per M6
    §0 lesson 4 — service ownership), and a persistence-layer matrix
    would duplicate the service invariants. If direct ORM writes ever
    become a problem, the check lives in ``clean()``; but M6.1 follows
    the M5.1 discipline of persistence-neutrality about workflow.

    **``Vehicle.price`` stays on Vehicle** (planning §1.2). The listing
    body reflects the current price at draft time; the price itself is
    the vehicle's identity and does not migrate to this model.

    **Publish semantics** (planning §5.e). ``status='published'`` means
    "visible to customers on the local ``/showroom`` endpoint." M6 v1
    does NOT push to Facebook Marketplace / AutoTrader / etc. — that's
    Milestone 11+.

    Source of truth: ``docs/roadmap/MILESTONE_6_PLANNING.md`` §1.2 +
    §5.a + §5.e.
    """

    vehicle = models.OneToOneField(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="listing",
    )
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="vehicle_listings",
    )
    status = models.CharField(
        max_length=16,
        choices=VEHICLE_LISTING_STATUS_CHOICES,
        default=VEHICLE_LISTING_STATUS_DRAFT,
    )
    title = models.CharField(max_length=255, blank=True, default="")
    # AI-drafted listing copy. Scrubbed via the M6.3 safety stack before
    # persistence (per §5.d — either reuse M4.5 ``_scrub_invented_recon_fact``
    # or add a new ``_scrub_invented_photo_claim``; decision deferred to
    # M6.3 implementation).
    body = models.TextField(blank=True, default="")
    # JSONField mapping (typically sentence indices or claim keys) to
    # source-bundle keys — mirrors :class:`VendorCommunication.source_provenance`.
    # Populated by the M6.3 draft service; default empty dict.
    source_provenance = models.JSONField(default=dict, blank=True)

    # Actor + timestamp provenance. Nullable at persistence layer; the
    # M6.3 service sets each pair atomically with the corresponding
    # transition. Persistence layer does NOT enforce required pairings —
    # that lives in the M6.3 service.
    drafted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    drafted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # Drives the M6.4 ``_rule_listing_to_frontline`` predicate
    # (``published_at is not None AND Vehicle.price > 0``).
    published_at = models.DateTimeField(null=True, blank=True)
    unpublished_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    unpublished_at = models.DateTimeField(null=True, blank=True)
    unpublished_reason = models.CharField(
        max_length=255, blank=True, default=""
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        verbose_name = "Vehicle listing"
        verbose_name_plural = "Vehicle listings"

    def __str__(self) -> str:
        return (
            f"{self.get_status_display()} listing on "
            f"vehicle #{self.vehicle_id}"
        )

    def clean(self) -> None:
        """Cross-tenant guard.

        The denormalized ``dealership`` FK must match the parent Vehicle's
        tenant. Mirrors :meth:`VehicleStage.clean`.
        """
        super().clean()
        if self.vehicle_id is None or self.dealership_id is None:
            return
        parent_dealership_id = getattr(self.vehicle, "dealership_id", None)
        if parent_dealership_id is None:
            return
        if parent_dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "VehicleListing.dealership must match the parent "
                        "Vehicle's dealership. Cross-tenant "
                        "contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 7 · Increment 1 — job-run observability substrate
# ---------------------------------------------------------------------------

JOB_RUN_STATUS_STARTED = "started"
JOB_RUN_STATUS_SUCCEEDED = "succeeded"
JOB_RUN_STATUS_FAILED = "failed"
JOB_RUN_STATUS_RETRIED = "retried"

JOB_RUN_STATUS_CHOICES = (
    (JOB_RUN_STATUS_STARTED, "Started"),
    (JOB_RUN_STATUS_SUCCEEDED, "Succeeded"),
    (JOB_RUN_STATUS_FAILED, "Failed"),
    (JOB_RUN_STATUS_RETRIED, "Retried"),
)


class JobRunLog(models.Model):
    """Milestone 7 · Increment 1 — one row per Celery task invocation.

    The observability substrate for every :func:`@instrumented_task`
    invocation across M7.2-M7.5 scheduled jobs (and any ad-hoc
    ``services/**/tasks.py`` module that opts in). Writes happen on
    task start and task end (success / failure / retry) — the pair
    lets an operator answer three questions from ``manage.py shell``,
    the Django admin, or a future M8 dashboard:

    1. *Did the scheduled job actually run?* (row exists with matching
       ``task_name``).
    2. *How long did it take?* (``duration_ms``).
    3. *Did it fail, and if so, what did it say?* (``status='failed'``
       + ``error_message``).

    **Chosen at §5.e Option A** (user-confirmed at SESSION_088 open).
    Prometheus counters (Option B) are deferred until the deploy stack
    grows a Prometheus scrape target; when it does, an additive
    decorator can wrap this model's write path without touching job
    authors.

    **Tenant-scoped when knowable.** The ``dealership`` FK is nullable
    because some job runs are process-wide (e.g. a future "vacuum
    orphaned rows across all tenants" reaper). Jobs that operate on a
    single tenant thread that tenant through as an
    :func:`@instrumented_task` context kwarg; the decorator writes
    ``dealership_id`` on both the start and end rows.

    **``args_summary`` is a truncated repr, not the full payload.**
    Celery task args may contain user-supplied strings; storing the
    full payload would risk leaking sensitive data into a queryable
    log table. The decorator truncates to 255 chars — enough for
    forensic pattern-matching, short enough to sidestep the leak.
    The full payload is available on the broker until the task
    completes; if forensic recovery is ever needed, a separate
    structured-log substrate is the right home.

    **Cross-tenant guard.** ``clean()`` is a no-op — this model has no
    parent-tenant relation (a job run is a top-level artifact). The
    :func:`services.tenancy._auto_attach_default_dealership` signal
    still fires because ``JobRunLog`` is in the
    ``_TENANT_CARRIER_MODEL_NAMES`` tuple (M7.1 extension 19 → 20),
    but the resolver's parent-inheritance branch is unreachable for
    this model (no ``session_id`` field), so the fallback path is
    always "attach the default tenant" — which is the right posture
    for jobs that were kicked off with no explicit tenant context.

    Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.7 +
    §5.e (Option A) + §7 M7.1.
    """

    # Dotted task path (e.g. ``services.floor_plan.tasks.accrue_daily_interest``).
    # Indexed because the M8 dashboard's primary query is
    # ``.filter(task_name=X).order_by('-started_at')``.
    task_name = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=JOB_RUN_STATUS_CHOICES,
        db_index=True,
    )
    # Set at start-log write time. Immutable — the end-log write goes
    # to the *same row* via ``update_fields=('status', 'ended_at', ...)``
    # so ``started_at`` never changes.
    started_at = models.DateTimeField()
    # Nullable at start-log write time — filled on end-log write
    # (success / failure / retry).
    ended_at = models.DateTimeField(null=True, blank=True)
    # Whole-millisecond duration. Computed at end-log write time as
    # ``(ended_at - started_at).total_seconds() * 1000`` and stamped
    # onto the row. Nullable until the end-log write.
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    # Non-blank on ``status='failed'`` end-log writes. Truncated
    # summary of the exception's ``__str__`` (full traceback lives in
    # the structured log stream, not in this table).
    error_message = models.TextField(blank=True, default="")
    # Truncated repr of ``args + kwargs``, max 255 chars. See class
    # docstring for the leak-avoidance rationale.
    args_summary = models.CharField(max_length=255, blank=True, default="")
    # Nullable — some jobs are process-wide. When set, the value is
    # populated by the :func:`@instrumented_task` decorator from a
    # ``dealership_id`` kwarg on the task invocation. Cross-tenant
    # ``clean()`` is a no-op (no parent record to compare against).
    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_run_logs",
    )

    class Meta:
        # ``-started_at`` first so the M8 dashboard's default view
        # (most-recent first) is a straight index scan.
        ordering = ("-started_at",)
        verbose_name = "Job run log"
        verbose_name_plural = "Job run logs"
        indexes = [
            # Support the "did *this* job run in the last N days?" query
            # per-tenant without a full-table scan. Composite because
            # both fields are frequently constrained together on the M8
            # dashboards.
            models.Index(
                fields=("task_name", "-started_at"),
                name="jrl_task_started_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.task_name} [{self.status}] @ {self.started_at:%Y-%m-%d %H:%M:%S}"


# ---------------------------------------------------------------------------
# Milestone 7 · Increment 3 — aging-per-stage snapshot substrate
# ---------------------------------------------------------------------------


class StageAgingSnapshot(models.Model):
    """Milestone 7 · Increment 3 — periodic per-stage aging snapshot.

    One row per ``(dealership, stage, snapshot_at)`` tuple. Records how
    many vehicles are currently in a given lifecycle stage and the
    distribution of "days spent in stage" across them, expressed as
    :attr:`vehicle_count` + :attr:`p50_days` (median) +
    :attr:`p90_days` (90th percentile).

    **Chosen at §5.c Option A** (user-confirmed at SESSION_088 open) —
    persist snapshots rather than compute-on-read at M8 endpoint time.
    Rationale: predictable dashboard latency at M8 justifies the extra
    model + scheduled job. On-read aggregation would scan every
    :class:`VehicleStage` row per request.

    **The row is the M7.3 job's output.** The
    :func:`services.lifecycle_aging.snapshots.snapshot_stage_ages`
    verb writes one row per stage-with-vehicles for one tenant. Stages
    with zero vehicles at snapshot time produce no rows — the M8
    dashboard interprets absence as "no vehicles here right now."

    **Percentile semantics.** ``p50_days`` is the median of "days
    between :attr:`VehicleStage.entered_at` and snapshot time" across
    every vehicle currently in the stage. ``p90_days`` is the 90th
    percentile — the "long tail" days-in-stage the operator should
    triage. Values are whole days (rounded down at computation time)
    so aging on a fresh vehicle can read 0.

    **Cross-tenant guard.** ``clean()`` is a no-op — the model has no
    parent-tenant relation to compare against (unlike VehiclePhoto ⇐
    Vehicle). The M7.3 verb writes ``dealership`` explicitly on every
    row; the M7.1 tenant-carrier autofill signal fills in the default
    tenant as a safety-net path if a caller bypasses the verb.

    Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.3 +
    §5.c (Option A) + §7 M7.3.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="stage_aging_snapshots",
    )
    # The lifecycle stage this snapshot describes. Uses the M5
    # ``VEHICLE_STAGE_CHOICES`` vocabulary — M7.3 does not introduce
    # new stage values.
    stage = models.CharField(
        max_length=32,
        choices=VEHICLE_STAGE_CHOICES,
    )
    # Snapshot wall-clock time. Populated by the verb at write time so
    # M8 aggregations can bucket by (stage, snapshot_at) without a
    # separate ``captured_at`` field.
    snapshot_at = models.DateTimeField(db_index=True)
    vehicle_count = models.PositiveIntegerField()
    # Whole-day p50 (median) days-in-stage across
    # ``vehicle_count`` vehicles. Zero is a legal value —
    # a vehicle that entered its current stage today reads 0 days.
    p50_days = models.PositiveIntegerField()
    p90_days = models.PositiveIntegerField()

    class Meta:
        # ``-snapshot_at`` first so the M8 dashboard's default "most-
        # recent snapshot first" view is a straight index scan.
        ordering = ("-snapshot_at", "stage")
        verbose_name = "Stage aging snapshot"
        verbose_name_plural = "Stage aging snapshots"
        indexes = [
            # Support the "aging history for tenant X, stage Y" query
            # per M8 dashboards without a full-table scan. Composite
            # because the M8 aggregation always constrains all three
            # columns together.
            models.Index(
                fields=("dealership", "stage", "-snapshot_at"),
                name="sas_tenant_stage_time_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_stage_display()} aging "
            f"(n={self.vehicle_count}, "
            f"p50={self.p50_days}d, p90={self.p90_days}d) "
            f"@ {self.snapshot_at:%Y-%m-%d %H:%M}"
        )


# ---------------------------------------------------------------------------
# Milestone 8 · Increment 1 — SLA-breach materialization substrate
# ---------------------------------------------------------------------------

# Breach-kind vocabulary — MUST stay in lockstep with the string
# constants that live inside
# ``dealer_ai.services.vendor_sla.detection``. Duplicated here (rather
# than imported) because ``models.py`` must not import service modules
# at load time. The M8.1 verb-extension writes rows using the same
# string values the M7.4 detection module emits into the log stream, so
# the two surfaces are wire-compatible.
SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA = "in_progress_past_eta"
SLA_BREACH_KIND_APPROVED_STALE = "approved_stale"

SLA_BREACH_KIND_CHOICES = (
    (SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA, "In progress past ETA"),
    (SLA_BREACH_KIND_APPROVED_STALE, "Approved stale"),
)


class SlaBreachRecord(models.Model):
    """Milestone 8 · Increment 1 — one row per detected SLA breach.

    The materialized counterpart to the M7.4
    :func:`services.vendor_sla.detect_sla_breaches` verb's
    ``logging.WARNING`` records. Chosen at
    :doc:`../roadmap/MILESTONE_8_PLANNING.md` §5.b Option B (user-
    confirmed at SESSION_094 open) — the log stream is not queryable
    substrate for M8 dashboards, so the M7.4 verb writes an
    ``SlaBreachRecord`` row per breach in addition to the log
    warning. M8.3 (:func:`services.analytics.sla_breaches.breach_patterns`)
    reads this table.

    **Idempotency invariant.** ``(work_order, kind, detected_at_date)``
    is unique. Same-day re-scans of the same tenant produce zero new
    rows — the M7.4 verb uses ``get_or_create`` on this triple. This
    mirrors the M2 floor-plan accrual idempotency pattern
    (``VehicleCost.reference='ACCRUAL:<iso-date>'``): re-running the
    scheduled job posts nothing new.

    **Denormalized ``vehicle_stock`` + ``vendor_name``.** Captured at
    detection time rather than joined on read. Rationale: the M8
    dashboards need the human-readable identifiers alongside every
    breach row, and denormalizing lets those queries stay single-table
    aggregations. Historical accuracy also survives vendor renames /
    vehicle stock-number changes — the row shows what the operator
    would have seen at breach time.

    **Cross-tenant guard.** ``clean()`` is a no-op — the model has no
    parent-tenant relation to compare against (unlike
    ``VehicleAcquisition`` ⇐ ``Vehicle``). The M7.4 verb-extension
    writes ``dealership`` explicitly on every row; the M7.1 tenant-
    carrier autofill signal fills in the default tenant as a safety-
    net path if a caller bypasses the verb.

    Source of truth: ``docs/roadmap/MILESTONE_8_PLANNING.md`` §1.5 +
    §5.b (Option B) + §7 M8.1.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="sla_breach_records",
    )
    # CASCADE — a WorkOrder deletion (rare; the M4 model has no
    # public DELETE surface) implicitly retracts its breach history.
    # M8 aggregations that project breaches per WO become meaningless
    # once the WO is gone, so cascading is the right shape.
    work_order = models.ForeignKey(
        "WorkOrder",
        on_delete=models.CASCADE,
        related_name="sla_breach_records",
    )
    kind = models.CharField(
        max_length=32,
        choices=SLA_BREACH_KIND_CHOICES,
    )
    # Whole days past the SLA threshold at detection time.
    # ``in_progress_past_eta`` = ``(as_of - estimated_completion_date).days``
    # (positive integer starting at 1 on the first day past ETA).
    # ``approved_stale`` = ``(as_of - approved_at.date()).days`` (an
    # integer > 7 by construction — the threshold constant).
    breach_days = models.PositiveIntegerField()
    # Wall-clock detection time. Populated at
    # ``get_or_create`` time by the M7.4 verb extension. The M8
    # dashboards bucket by ``detected_at`` for the "breach patterns
    # in the last N days" query.
    detected_at = models.DateTimeField(db_index=True)
    # Denormalized date derived from ``detected_at``. Populated
    # explicitly by the verb (not via a generated column) so the
    # unique constraint below is enforceable on every supported
    # backend without engine-specific SQL. The M7.4 daily scan
    # writes one row per breach-kind per WO per calendar day; same-
    # day re-runs collide on this triple and no-op.
    detected_at_date = models.DateField()
    # Denormalized identifiers — see class docstring for the "historical
    # accuracy survives rename" rationale.
    vehicle_stock = models.CharField(max_length=64)
    vendor_name = models.CharField(max_length=255)

    class Meta:
        # ``-detected_at`` first so the M8 dashboard's default view
        # (most-recent-first) is a straight index scan.
        ordering = ("-detected_at",)
        verbose_name = "SLA breach record"
        verbose_name_plural = "SLA breach records"
        constraints = [
            # Idempotency for the M7.4 daily scan — same-day re-runs
            # post zero new rows.
            models.UniqueConstraint(
                fields=("work_order", "kind", "detected_at_date"),
                name="sbr_wo_kind_date_uq",
            ),
        ]
        indexes = [
            # Support the "breach pattern for tenant X, kind Y" query
            # per M8.3 dashboards without a full-table scan. Composite
            # because the M8 aggregation always constrains all three
            # columns together.
            models.Index(
                fields=("dealership", "kind", "-detected_at"),
                name="sbr_tenant_kind_time_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_kind_display()} on "
            f"WO #{self.work_order_id} "
            f"(vehicle={self.vehicle_stock}, "
            f"vendor={self.vendor_name}, "
            f"{self.breach_days}d) "
            f"@ {self.detected_at:%Y-%m-%d %H:%M}"
        )


# ---------------------------------------------------------------------------
# Milestone 9 · Increment 1 (SESSION_100) — Sale entity vocabulary.
# ---------------------------------------------------------------------------

# Sale finance-type vocabulary — MILESTONE_9_PLANNING.md §5.c Option A
# (user-confirmed at SESSION_100 open, recorded in §0.a). Three
# initial values match the M8 planning §1.6 catalog. Extensions
# (`lease`, `wholesale_out`, `internal_transfer`,
# `wholesale_disposal`) land when operator evidence surfaces need,
# per §5.c Option B (deferred).
SALE_FINANCE_TYPE_CASH = "cash"
SALE_FINANCE_TYPE_RETAIL = "retail"
SALE_FINANCE_TYPE_BHPH = "bhph"

SALE_FINANCE_TYPE_CHOICES = (
    (SALE_FINANCE_TYPE_CASH, "Cash"),
    (SALE_FINANCE_TYPE_RETAIL, "Retail (bank / credit union)"),
    (SALE_FINANCE_TYPE_BHPH, "Buy-here-pay-here"),
)


class Sale(models.Model):
    """Milestone 9 · Increment 1 — one Sale per Vehicle.

    Persists the closing event that turns a Vehicle from inventory
    into a completed transaction. OneToOne on ``vehicle`` — the
    business invariant "a car sells exactly once from this dealer's
    lot" is enforced at the schema level.

    Every business question Milestone 9 answers ("what did we
    realize on this sale?", "what's the gross-profit trend?", "what
    is true days-to-sale for this vehicle-type?") starts from this
    row plus the M2 ledger. See
    ``docs/roadmap/MILESTONE_9_PLANNING.md`` §1.1 for the field
    contract and §1.4 for the ``gross_realized`` computation
    contract.

    **`buyer` FK to `CustomerLead`** — §5.b Option A (user-
    confirmed at SESSION_100 open). Reuses the M3-M5 CRM
    substrate: the customer already exists as a lead by the time a
    Sale writes. Nullable + SET_NULL so historical CustomerLead
    deletion doesn't cascade into the Sale record (the Sale itself
    is the ledger of record; the lead is provenance context).

    **`gross_realized` denormalized on the row** — populated at
    write time by :func:`services.sale.record_sale` via
    :func:`services.sale.computation.gross_realized`. Stored (not
    computed on read) so M9.3 analytics queries can aggregate
    without per-row ledger recomputation. The verb is pure — same
    ``sale`` + same DB state → same Decimal — so the stored value
    can be re-derived at any time if the ledger evolves.

    **Cross-tenant guard.** ``clean()`` enforces two invariants —
    ``dealership`` must match ``vehicle.dealership`` and, when
    ``buyer`` is set, ``buyer.dealership``. Belt (model) +
    suspenders (service layer's
    :class:`services.sale.CrossTenantSaleError`).
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="sales",
    )
    vehicle = models.OneToOneField(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="sale",
    )
    # §5.b Option A: FK to CustomerLead. SET_NULL so lead deletion
    # doesn't retract the Sale record — the Sale is the source of
    # truth for the closing event, the lead is context provenance.
    buyer = models.ForeignKey(
        "CustomerLead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )
    sale_date = models.DateField()
    sold_price = models.DecimalField(max_digits=10, decimal_places=2)
    finance_type = models.CharField(
        max_length=32,
        choices=SALE_FINANCE_TYPE_CHOICES,
    )
    # Free text until a Lender entity emerges (deferred beyond M9).
    # Blank for cash sales (finance_type='cash') — the service layer
    # requires a non-empty value only when finance_type != 'cash'.
    lender_name = models.CharField(max_length=255, blank=True, default="")
    # Denormalized ledger read — computed at Sale write time by the
    # service verb per §1.4. Signed Decimal (negative when the sale
    # closed below total_investment).
    gross_realized = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-sale_date", "-created_at")
        verbose_name = "Sale"
        verbose_name_plural = "Sales"

    def __str__(self) -> str:
        return (
            f"Sale #{self.pk} of #{self.vehicle.stock_number} "
            f"@ ${self.sold_price} ({self.get_finance_type_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guards at the model layer.

        Two invariants:

        1. ``dealership`` must match ``vehicle.dealership`` — mirrors
           :meth:`VehicleAcquisition.clean` /
           :meth:`VehicleCost.clean`. A mis-scoped view resolving
           tenant from ``get_current_dealership(request)`` and
           writing a Sale against a vehicle owned by a different
           dealership would silently corrupt tenant scoping.
        2. When ``buyer`` is set, ``buyer.dealership`` must match
           ``dealership`` — prevents a Sale at Dealership A from
           referencing a lead at Dealership B.

        Both raise before the row reaches the DB. Data-scoping is
        layer 4 in ``AUTHENTICATION_MODEL.md`` §1.
        """
        super().clean()
        if self.vehicle_id is None or self.dealership_id is None:
            return
        if self.vehicle.dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "Sale.dealership must match the parent Vehicle's "
                        "dealership. Cross-tenant contamination guard "
                        "(see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )
        if (
            self.buyer_id is not None
            and self.buyer.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "buyer": (
                        "Sale.buyer must belong to the same dealership as "
                        "the Sale. Cross-tenant contamination guard "
                        "(see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 9 · Increment 2 (SESSION_101) — Delivery entity vocabulary.
# ---------------------------------------------------------------------------

# Delivery checklist item vocabulary per MILESTONE_9_PLANNING.md §1.2.
# Five initial keys from SALES_DEPARTMENT_MAPPING.md §delivery workflow.
# Extensions (`walkaround_video`, `key_fob_pairing`, `plate_bracket_installed`,
# `owner_manual_walkthrough`, `service_intro`) land when operator evidence
# surfaces need. Kept as module-level constants so
# ``services.delivery.update_checklist_item`` and the M9.2 tests import
# the canonical string literals without redeclaring (mirrors the
# ``SALE_FINANCE_TYPE_*`` pattern above).
DELIVERY_CHECKLIST_DETAIL_BOOKED = "detail_booked"
DELIVERY_CHECKLIST_FUELED = "fueled"
DELIVERY_CHECKLIST_TEMP_TAG = "temp_tag"
DELIVERY_CHECKLIST_INSURANCE_VERIFIED = "insurance_verified"
DELIVERY_CHECKLIST_CUSTOMER_WALKTHROUGH = "customer_walkthrough"

DELIVERY_CHECKLIST_KEYS = (
    DELIVERY_CHECKLIST_DETAIL_BOOKED,
    DELIVERY_CHECKLIST_FUELED,
    DELIVERY_CHECKLIST_TEMP_TAG,
    DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
    DELIVERY_CHECKLIST_CUSTOMER_WALKTHROUGH,
)


def _default_delivery_checklist() -> dict:
    """Return a fresh dict with every M9.2 checklist key set to False.

    Used as the ``default=`` callable on :attr:`Delivery.checklist` so
    every new row starts with an unchecked checklist that renders the
    same shape (no missing keys) as a fully-populated row. Passing a
    callable rather than a dict literal follows Django's guidance for
    mutable field defaults.
    """
    return {key: False for key in DELIVERY_CHECKLIST_KEYS}


class Delivery(models.Model):
    """Milestone 9 · Increment 2 — one Delivery per Sale.

    Persists the delivery-preparation workflow that a Sale
    transitions through before the customer takes possession.
    OneToOne on ``sale`` (mandatory per
    ``MILESTONE_9_PLANNING.md`` §1.2 Option A — user-confirmed at
    SESSION_101 open, recorded in §0.a). Cash-and-carry sales
    still get a Delivery row; the ``checklist`` just carries fewer
    keys marked False at creation time.

    Business questions answered — Q2 from
    :doc:`../../docs/roadmap/MILESTONE_9_PLANNING.md` §1.0. Locks
    the "what pieces of a delivery are tracked to completion?"
    surface (five checklist keys + temp-tag + insurance
    verification + free-text notes).

    **Denormalized ``dealership`` FK.** Same rationale as
    :class:`Sale.dealership` — the parent ``sale.dealership`` is
    the source of truth, but the redundant FK lets tenant-scoped
    querysets skip a join. ``clean()`` enforces the invariant.

    **`checklist` JSONField.** Populated at write time with every
    M9.2 key set to False via
    :func:`_default_delivery_checklist`. Callers toggle individual
    items via
    :func:`services.delivery.update_checklist_item`; extra keys
    are refused (:class:`services.delivery.UnknownChecklistKeyError`)
    so the vocabulary stays authoritative at the service layer.
    Historical rows survive vocabulary extensions — new keys land
    as False on subsequent Delivery rows without a data migration.

    **Insurance columns are denormalized from the checklist.**
    ``insurance_verified`` (boolean) + ``insurance_verified_at``
    (timestamp) mirror the ``insurance_verified`` checklist key
    but as queryable columns. Rationale: verifying insurance
    before delivery is a legal-compliance moment (many states
    require proof-of-insurance at title transfer), so operator
    dashboards and future compliance reports need to filter and
    aggregate on it without JSON extraction. The
    :func:`services.delivery.verify_insurance` verb writes both
    the column and the checklist key atomically.

    **Cross-tenant guard.** ``clean()`` enforces
    ``dealership`` matches ``sale.dealership``. Belt (model) +
    suspenders (service layer's
    :class:`services.delivery.CrossTenantDeliveryError`).
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    sale = models.OneToOneField(
        "Sale",
        on_delete=models.CASCADE,
        related_name="delivery",
    )
    delivery_date = models.DateField(null=True, blank=True)
    # Populated at insert time via ``_default_delivery_checklist`` so
    # every row renders the same shape. Toggled item-by-item via the
    # M9.2 update verb. Refuses keys outside the M9.2 vocabulary.
    checklist = models.JSONField(default=_default_delivery_checklist, blank=True)
    temp_tag_number = models.CharField(max_length=32, blank=True, default="")
    # Denormalized boolean + timestamp mirroring the
    # ``insurance_verified`` checklist key — see class docstring for
    # the "compliance moment" rationale.
    insurance_verified = models.BooleanField(default=False)
    insurance_verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Delivery"
        verbose_name_plural = "Deliveries"

    def __str__(self) -> str:
        # Sale.__str__ already renders the vehicle stock number, so
        # inlining the sale summary keeps the delivery string
        # scannable without a second attribute lookup.
        return (
            f"Delivery #{self.pk} for Sale #{self.sale_id} "
            f"(insurance_verified={self.insurance_verified})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer.

        The denormalized ``dealership`` FK must match the parent
        Sale's tenant. Mirrors :meth:`Sale.clean` /
        :meth:`VehicleAcquisition.clean` / :meth:`VehicleCost.clean`.
        Data-scoping is layer 4 in ``AUTHENTICATION_MODEL.md`` §1.
        """
        super().clean()
        if self.sale_id is None or self.dealership_id is None:
            return
        if self.sale.dealership_id != self.dealership_id:
            raise ValidationError(
                {
                    "dealership": (
                        "Delivery.dealership must match the parent "
                        "Sale's dealership. Cross-tenant contamination "
                        "guard (see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 1 (SESSION_106) — CreditApplication vocabulary.
# ---------------------------------------------------------------------------

# CreditApplication source-format vocabulary per
# FINANCE_DEPARTMENT_MAPPING.md §1.1 (three formats: paper on a
# clipboard, in-store tablet or terminal, online pre-qualification
# form). Kept as module-level constants so
# ``services.f_and_i.record_credit_application`` and the M10.1 tests
# import the canonical literals without redeclaring — mirrors the
# ``SALE_FINANCE_TYPE_*`` / ``DELIVERY_CHECKLIST_*`` pattern.
CREDIT_APP_FORMAT_PAPER = "paper"
CREDIT_APP_FORMAT_TABLET = "tablet"
CREDIT_APP_FORMAT_ONLINE_PREQUAL = "online_prequal"

CREDIT_APP_FORMAT_CHOICES = (
    (CREDIT_APP_FORMAT_PAPER, "Paper (clipboard)"),
    (CREDIT_APP_FORMAT_TABLET, "In-store tablet / terminal"),
    (CREDIT_APP_FORMAT_ONLINE_PREQUAL, "Online pre-qualification"),
)

# CreditApplication status vocabulary. Deliberately small at M10.1
# per PROJECT_RULES.md rule 4 (scope discipline). Extensions
# (``approved`` / ``declined`` / ``adverse_action``) belong to
# per-lender state and land with :class:`LenderSubmission` at M10.3
# — see MILESTONE_10_PLANNING.md §7 M10.3. The M10.1 vocabulary
# captures only the states the platform can determine from its own
# actions.
CREDIT_APP_STATUS_RECEIVED = "received"
CREDIT_APP_STATUS_SUBMITTED = "submitted"
CREDIT_APP_STATUS_WITHDRAWN = "withdrawn"

CREDIT_APP_STATUS_CHOICES = (
    (CREDIT_APP_STATUS_RECEIVED, "Received (not yet submitted)"),
    (CREDIT_APP_STATUS_SUBMITTED, "Submitted to lender(s)"),
    (CREDIT_APP_STATUS_WITHDRAWN, "Withdrawn"),
)

# Retention window per FINANCE_DEPARTMENT_MAPPING.md §6.9 (federal
# + state rules range 2 years for some paper documents to 5-7 years
# for most transaction records). Conservative default of 7 years
# covers the upper bound. Stored as a module constant (not a Django
# setting) so the invariant "credit apps are retained ≥7 years from
# capture" is source-of-truth in the code, not overridable per
# environment.
CREDIT_APP_RETENTION_YEARS = 7


class CreditApplicationRetentionActiveError(RuntimeError):
    """Raised when :meth:`CreditApplication.delete` is called on a
    row whose ``retention_expires_at`` is still in the future.

    Model-layer enforcement per MILESTONE_10_PLANNING.md §5.e —
    retention clocks are locked at the model layer so a service-only
    guard can't be bypassed by an ad-hoc ``.delete()`` call, Django
    admin action, or cascade from an unrelated model. The invariant
    "credit apps are retained ≥7 years from capture" is the model's
    responsibility to hold.
    """


class CreditApplication(models.Model):
    """Milestone 10 · Increment 1 — the customer credit application.

    Captures the credit-application intake step of the F&I workflow
    per ``FINANCE_DEPARTMENT_MAPPING.md`` §1.1 — the written or
    electronic form on which the customer authorizes the dealer to
    pull their credit and submit their information to lenders.

    **Attach shape — nullable FKs to both `CustomerLead` and `Sale`**
    per ``MILESTONE_10_PLANNING.md`` §5.a Option C (user-confirmed at
    SESSION_106 open, recorded in §0.a). Credit apps intake at lead
    time (``lead`` FK set, ``sale`` FK null); on sale close the
    ``sale`` FK is set (``lead`` FK preserved). ``clean()`` requires
    at least one of the two to be set — the app must attach to
    something in-tenant. Neither FK cascades; ``SET_NULL`` on both
    preserves the credit-application row (the retention-clock record
    of record) if either parent is deleted.

    **Retention clock — locked at the model layer.** ``captured_at``
    starts the clock; ``retention_expires_at`` is computed at write
    time as ``captured_at + CREDIT_APP_RETENTION_YEARS``. The
    :meth:`delete` override refuses any delete before
    ``retention_expires_at``, raising
    :class:`CreditApplicationRetentionActiveError`. This is per
    ``MILESTONE_10_PLANNING.md`` §5.e — service-only enforcement
    would let ad-hoc callers (Django admin action, management
    command, cascade from a future related model) bypass the
    invariant. The model holds the line.

    **Minimal PII surface at M10.1.** Full applicant identity
    (full SSN, DOB, driver's-license number, address) surfaces at
    M10.2+ when the Safeguards Rule technical-controls layer is in
    scope (encryption at rest, access logging, field-level ACLs
    per FINANCE §6.4). At M10.1 the model captures ``applicant_full_name``
    (identity for operator lookup) and optionally
    ``applicant_ssn_last4`` (for lender-portal correlation), both
    plain-text at rest. Storing full SSN before the technical-controls
    layer ships would violate the Safeguards Rule; the schema is
    intentionally narrow so M10.1 cannot become a compliance-debt
    substrate.

    **Cross-tenant guard.** ``clean()`` enforces that whichever
    parent FK is set (``lead`` or ``sale``) belongs to the same
    dealership as the credit application. Mirrors :meth:`Sale.clean`
    / :meth:`Delivery.clean` / :meth:`VehicleAcquisition.clean`.
    Belt (model) + suspenders (service layer's
    :class:`services.f_and_i.CrossTenantCreditApplicationError`).
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="credit_applications",
    )
    # §5.a Option C: FKs to both CustomerLead and Sale, nullable +
    # SET_NULL. Credit apps outlive both parents (retention clock is
    # the record of record). ``clean()`` requires at least one set.
    lead = models.ForeignKey(
        "CustomerLead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_applications",
    )
    sale = models.ForeignKey(
        "Sale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_applications",
    )
    applicant_full_name = models.CharField(max_length=255)
    # Last-4 only at M10.1 (full-SSN handling deferred until the
    # Safeguards Rule technical-controls layer lands). Blank
    # permitted for pre-qualification apps that haven't collected
    # SSN yet.
    applicant_ssn_last4 = models.CharField(max_length=4, blank=True, default="")
    # M10.2 additive extension per MILESTONE_10_PLANNING.md §1.2.a
    # Option A (user-confirmed at SESSION_107 open, recorded in
    # §0.a). Nullable Decimals so M10.1-era rows survive with
    # NULL — the M10.2 PTI / DTI ratio verbs return ``None`` when
    # either column is unset rather than raising, per the "old
    # rows survive vocabulary extensions" pattern from
    # ``Delivery.checklist``. Both fields are native credit-app
    # data per FINANCE §1.5 (income) + §1.10 (bureau debt totals).
    gross_monthly_income = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    existing_monthly_debt = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    source_format = models.CharField(
        max_length=32,
        choices=CREDIT_APP_FORMAT_CHOICES,
    )
    status = models.CharField(
        max_length=32,
        choices=CREDIT_APP_STATUS_CHOICES,
        default=CREDIT_APP_STATUS_RECEIVED,
    )
    # ``captured_at`` starts the retention clock. Distinct from
    # ``created_at`` (row insert time) because a paper app may be
    # captured on paper hours or days before it lands in the
    # system. Callers can override; the service defaults to
    # ``timezone.now()`` if omitted.
    captured_at = models.DateTimeField()
    # Denormalized from ``captured_at + CREDIT_APP_RETENTION_YEARS``
    # at write time by the service verb. Stored (not computed on
    # read) so retention-audit queries can filter without per-row
    # date arithmetic. :meth:`delete` reads this column directly to
    # decide whether to allow the delete.
    retention_expires_at = models.DateTimeField()
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-captured_at", "-created_at")
        verbose_name = "Credit application"
        verbose_name_plural = "Credit applications"

    def __str__(self) -> str:
        return (
            f"CreditApplication #{self.pk} — "
            f"{self.applicant_full_name} ({self.get_status_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination + attach-shape guards at the model layer.

        Three invariants (§5.a Option C):

        1. At least one of ``lead`` / ``sale`` is set — the app must
           attach to an in-tenant parent. A credit app with both FKs
           null has no operational anchor and no way to be found by
           lead-scoped or sale-scoped operator queries.
        2. When ``lead`` is set, ``lead.dealership`` must match
           ``dealership``. Prevents cross-tenant contamination via
           lead assignment.
        3. When ``sale`` is set, ``sale.dealership`` must match
           ``dealership``. Same guard on the sale side.

        Retention-clock consistency (``retention_expires_at`` must be
        ≥ ``captured_at``) is enforced by the service verb, not the
        model — a raw ``.save()`` with an incoherent retention date
        surfaces the invariant at the compliance query layer where
        it matters, and Django's clean() cannot enforce it without
        also requiring the service to bypass ``clean()`` (which
        would defeat the model-layer guard on the FK invariants).
        """
        super().clean()
        if self.dealership_id is None:
            return
        if self.lead_id is None and self.sale_id is None:
            raise ValidationError(
                {
                    "__all__": (
                        "CreditApplication must attach to at least one "
                        "of lead or sale (see MILESTONE_10_PLANNING.md "
                        "§5.a Option C)."
                    )
                }
            )
        if (
            self.lead_id is not None
            and self.lead.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lead": (
                        "CreditApplication.lead must belong to the same "
                        "dealership as the CreditApplication. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )
        if (
            self.sale_id is not None
            and self.sale.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "sale": (
                        "CreditApplication.sale must belong to the same "
                        "dealership as the CreditApplication. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )

    def delete(self, *args, **kwargs):
        """Refuse delete while the retention window is still active.

        Per MILESTONE_10_PLANNING.md §5.e — retention is a model-layer
        invariant. Compares ``retention_expires_at`` against
        :func:`django.utils.timezone.now`. Raises
        :class:`CreditApplicationRetentionActiveError` when the
        window is still open.

        Callers that need to purge an expired app call ``.delete()``
        normally after the window closes. There is no ``force=``
        escape hatch — if operators need to purge an unexpired
        record for a specific compliance reason (a customer's
        deletion request under a state privacy law), that surface
        lands as a discrete verb in the compliance-workflow
        increment (M10.7), not here.
        """
        if self.retention_expires_at is not None and (
            timezone.now() < self.retention_expires_at
        ):
            raise CreditApplicationRetentionActiveError(
                f"CreditApplication #{self.pk} is still within its "
                f"retention window (expires {self.retention_expires_at.isoformat()}). "
                f"Refusing delete."
            )
        return super().delete(*args, **kwargs)


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 2 (SESSION_107) — DealStructure entity.
# ---------------------------------------------------------------------------


class DealStructure(models.Model):
    """Milestone 10 · Increment 2 — the F&I deal-desk structuring row.

    Links a :class:`CreditApplication` to a specific :class:`Vehicle`
    with the deal-desk math the F&I manager assembles: sale price,
    cash down, trade allowance / payoff, taxes, fees, amount financed,
    APR, term, monthly payment, back-end products, and the three
    ratio metrics (LTV / PTI / DTI). Per
    ``MILESTONE_10_PLANNING.md`` §1.2 the model stores the deal
    inputs *and* the denormalized ratio outputs; the service verbs
    in :mod:`services.f_and_i.deal_structure` compute the ratios at
    write time and populate the ``*_pct`` columns for query-ability.

    **Attach shape.** FK to :class:`CreditApplication` (mandatory —
    the credit app is the operational parent; a deal structure
    without a credit app is nonsense in the F&I workflow) + FK to
    :class:`Vehicle` (mandatory — the specific unit being financed;
    a customer may desk multiple vehicles). Both FKs cascade —
    deleting either parent invalidates the deal structure. Multiple
    deal structures per credit application are allowed (F&I
    iterates: primary lender approval, subprime counter-offer,
    revised terms after a stip clears, etc.) — standard M-to-1, no
    unique constraint at M10.2.

    **APR unit convention.** Percent units (e.g. ``9.9900`` for
    9.99% APR), matching ``services.payment_engine`` — see
    ``payment_engine.DEFAULT_APR = 7.49`` and the docstring at
    ``services.payment_engine.py`` line 261. Consistent APR units
    across the payment-engine and F&I ratio surfaces are critical:
    every downstream ratio verb expects percent-unit APR.

    **Ratio denormalization.** ``ltv_pct`` / ``pti_pct`` /
    ``dti_pct`` are populated at write time by
    :func:`services.f_and_i.deal_structure.record_deal_structure`.
    Nullable — LTV requires ``sale_price > 0`` (else NULL); PTI
    and DTI require ``CreditApplication.gross_monthly_income``
    (and DTI also requires ``existing_monthly_debt``). For M10.1-
    era CreditApplication rows without income captured, PTI / DTI
    land as NULL and downstream compliance / dashboard filters
    treat NULL as "not computable" rather than "not applicable."

    **Cross-tenant guard.** ``clean()`` enforces that
    ``dealership`` matches both ``credit_application.dealership``
    and ``vehicle.dealership``. Mirrors :meth:`Sale.clean` /
    :meth:`Delivery.clean` / :meth:`CreditApplication.clean`. Belt
    (model) + suspenders (service layer's
    :class:`services.f_and_i.CrossTenantDealStructureError`).

    **`back_end_products` JSONField.** Free-form array at M10.2
    for VSC / GAP / paint-and-fabric / theft-etching / etc.
    Vocabulary partitioning (fixed set vs per-dealership catalog)
    is deferred until the M10.5 Contract entity lands and operator
    evidence surfaces the shape. Default empty list, matching
    ``Delivery.checklist`` empty-default pattern.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="deal_structures",
    )
    credit_application = models.ForeignKey(
        "CreditApplication",
        on_delete=models.CASCADE,
        related_name="deal_structures",
    )
    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
        related_name="deal_structures",
    )
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    down_payment = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    trade_allowance = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    trade_payoff = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    taxes = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    fees = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    amount_financed = models.DecimalField(max_digits=10, decimal_places=2)
    # Percent units — matches ``services.payment_engine`` convention
    # (``DEFAULT_APR = 7.49  # %``). Up to 99.9999% precision.
    apr = models.DecimalField(max_digits=6, decimal_places=4)
    term_months = models.PositiveIntegerField()
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2)
    # Free-form array at M10.2 — vocabulary partitioning deferred
    # to M10.5 when Contract lands.
    back_end_products = models.JSONField(default=list, blank=True)
    # Denormalized ratio outputs — populated at write time by the
    # M10.2 service verbs. Nullable so M10.1-era CreditApplications
    # without income surface as "not computable" rather than 0.
    ltv_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    pti_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    dti_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Deal structure"
        verbose_name_plural = "Deal structures"

    def __str__(self) -> str:
        return (
            f"DealStructure #{self.pk} — "
            f"CA #{self.credit_application_id} × "
            f"Vehicle #{self.vehicle_id} "
            f"(${self.monthly_payment}/mo, APR {self.apr}%)"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guards at the model layer.

        Two invariants:

        1. ``dealership`` must match ``credit_application.dealership``.
        2. ``dealership`` must match ``vehicle.dealership``.

        Both raise before the row reaches the DB. Data-scoping is
        layer 4 in ``AUTHENTICATION_MODEL.md`` §1. Belt (model) +
        suspenders (service layer's
        :class:`services.f_and_i.CrossTenantDealStructureError`).
        """
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.credit_application_id is not None
            and self.credit_application.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "credit_application": (
                        "DealStructure.credit_application must belong to "
                        "the same dealership as the DealStructure. "
                        "Cross-tenant contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )
        if (
            self.vehicle_id is not None
            and self.vehicle.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "vehicle": (
                        "DealStructure.vehicle must belong to the same "
                        "dealership as the DealStructure. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 3 (SESSION_108) — LenderProgram vocabulary.
# ---------------------------------------------------------------------------

# LenderSubmission status vocabulary per MILESTONE_10_PLANNING.md
# §1.3.b Option A (user-confirmed at SESSION_108 open, recorded in
# §0.a). Fixed set of four values matching FINANCE §workflow step 9
# ("approval, conditional approval, counter-offer, or decline").
# Extensions (`withdrawn_by_dealer`, `expired`) land when operator
# evidence surfaces need. ``funded`` belongs to M10.5 as a Contract
# / Funding state, not a submission state.
LENDER_SUBMISSION_STATUS_PENDING = "pending"
LENDER_SUBMISSION_STATUS_APPROVED = "approved"
LENDER_SUBMISSION_STATUS_COUNTER = "counter"
LENDER_SUBMISSION_STATUS_DECLINED = "declined"

LENDER_SUBMISSION_STATUS_CHOICES = (
    (LENDER_SUBMISSION_STATUS_PENDING, "Pending"),
    (LENDER_SUBMISSION_STATUS_APPROVED, "Approved"),
    (LENDER_SUBMISSION_STATUS_COUNTER, "Counter-offer"),
    (LENDER_SUBMISSION_STATUS_DECLINED, "Declined"),
)


class LenderProgram(models.Model):
    """Milestone 10 · Increment 3 — per-dealership catalog entry for
    a lender program.

    Structured record of a lender program the dealership has an
    active relationship with. Per
    ``MILESTONE_10_PLANNING.md`` §1.3.c Option A (user-confirmed
    at SESSION_108 open, recorded in §0.a) — per-dealership scope
    with FK to :class:`Dealership`. Coexists with the free-text
    :attr:`DealerOnboardingProfile.subprime_lenders` field per §5.d
    Option C (SESSION_106) — the free-text field remains a notes
    area; this catalog is the structured surface that
    :class:`LenderSubmission` FKs into.

    **Uniqueness.** ``(dealership, name)`` unique — a dealership
    cannot have two programs with the same name. Deactivated
    programs (see ``is_active`` below) still occupy the name
    slot so re-adding "ABC Bank" with the same name after
    deactivation surfaces as a duplicate; operators either
    reactivate the existing row or use a distinct name.

    **`is_active` boolean.** Programs churn constantly per FINANCE
    §7.2 ("Program rate sheets sit in binders, in email inboxes,
    in portal messages, in the F&I manager's head. Programs
    change monthly (sometimes weekly)."). Deactivation is a soft
    delete — the row is preserved because
    :class:`LenderSubmission` protects against hard-delete (see
    the M10.3 submission model's ``on_delete=PROTECT``). The
    :func:`services.f_and_i.list_active_lender_programs` verb
    filters on this column for operator-facing lender pickers.

    **No back-fill of `subprime_lenders`.** Per §5.d Option C —
    operators re-populate the structured catalog manually. The
    free-text field is preserved for the transition period and
    beyond as a notes surface.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="lender_programs",
    )
    name = models.CharField(max_length=255)
    # Contact person / phone / email — free-form single line for
    # M10.3. If operators surface structured contact requirements
    # later, extend additively (e.g. ``contact_email`` +
    # ``contact_phone``) rather than rewriting.
    contact = models.CharField(max_length=255, blank=True, default="")
    # Free-text summary of current program terms (advance / tier
    # cutoffs / vehicle age caps / typical stips) — the "binder /
    # inbox / head" data from FINANCE §7.2 pulled into one place.
    terms_summary = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Lender program"
        verbose_name_plural = "Lender programs"
        constraints = [
            models.UniqueConstraint(
                fields=("dealership", "name"),
                name="unique_lender_program_name_per_dealership",
            ),
        ]

    def __str__(self) -> str:
        active = "active" if self.is_active else "inactive"
        return f"LenderProgram #{self.pk} — {self.name} ({active})"


class LenderSubmission(models.Model):
    """Milestone 10 · Increment 3 — a submission of a DealStructure
    to a LenderProgram.

    Persists the F&I workflow step of submitting a structured deal
    to a lender and tracking the response. Per FINANCE §workflow
    step 8-10: F&I structures the deal (M10.2), selects a lender,
    submits, and waits for approval / counter / decline.

    **Attach shape — mandatory FK to DealStructure** per
    ``MILESTONE_10_PLANNING.md`` §1.3.a Option A (user-confirmed
    at SESSION_108 open, recorded in §0.a). Every submission is
    *of* a deal structure to a lender; the CASCADE means deleting
    the deal structure invalidates the submission history.

    **FK to LenderProgram uses `on_delete=PROTECT`.** A program
    with submissions cannot be hard-deleted — the submissions are
    historical records for the F&I audit trail. Operators
    deactivate programs via :attr:`LenderProgram.is_active`
    instead of deleting them.

    **Status vocabulary.** Fixed four-value set per §1.3.b Option
    A: ``pending`` (default at write time) → ``approved`` /
    ``counter`` / ``declined``. No transition constraints at
    M10.3 — the service verb accepts any-to-any transition and
    operator behavior is captured as-recorded. Transition rules
    can be locked at M10.4 (Stipulation) or M10.7 (compliance)
    if evidence surfaces a need.

    **counter_terms / approval_terms.** Free-form JSONField per
    §1.3.d Option A. Whatever the lender's response contained.
    Vocabulary partitioning deferred to M10.7 compliance layer.
    Both default to empty dict so the row shape is stable
    regardless of status.

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches both ``deal_structure.dealership`` and
    ``lender_program.dealership``. Belt (model) + suspenders
    (service layer's :class:`services.f_and_i.CrossTenantLenderSubmissionError`).
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="lender_submissions",
    )
    deal_structure = models.ForeignKey(
        "DealStructure",
        on_delete=models.CASCADE,
        related_name="lender_submissions",
    )
    # PROTECT — a program with submissions is a historical record;
    # operators deactivate rather than delete.
    lender_program = models.ForeignKey(
        "LenderProgram",
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    submitted_at = models.DateTimeField()
    status = models.CharField(
        max_length=32,
        choices=LENDER_SUBMISSION_STATUS_CHOICES,
        default=LENDER_SUBMISSION_STATUS_PENDING,
    )
    # Free-form JSON per §1.3.d Option A. Default empty dict so the
    # row shape is stable across every status value.
    counter_terms = models.JSONField(default=dict, blank=True)
    approval_terms = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-submitted_at", "-created_at")
        verbose_name = "Lender submission"
        verbose_name_plural = "Lender submissions"

    def __str__(self) -> str:
        return (
            f"LenderSubmission #{self.pk} — DS #{self.deal_structure_id} "
            f"→ {self.lender_program.name} ({self.get_status_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guards at the model layer.

        Two invariants:

        1. ``dealership`` must match ``deal_structure.dealership``.
        2. ``dealership`` must match ``lender_program.dealership``.

        Both raise before the row reaches the DB. Data-scoping is
        layer 4 in ``AUTHENTICATION_MODEL.md`` §1.
        """
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.deal_structure_id is not None
            and self.deal_structure.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "deal_structure": (
                        "LenderSubmission.deal_structure must belong to "
                        "the same dealership as the LenderSubmission. "
                        "Cross-tenant contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )
        if (
            self.lender_program_id is not None
            and self.lender_program.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lender_program": (
                        "LenderSubmission.lender_program must belong to "
                        "the same dealership as the LenderSubmission. "
                        "Cross-tenant contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 4 (SESSION_109) — Stipulation vocabulary.
# ---------------------------------------------------------------------------

# Stipulation type vocabulary per MILESTONE_10_PLANNING.md §5.b
# Option A (user-confirmed at SESSION_106 open, recorded in §0.a).
# Small fixed set covering the FINANCE §1.9 catalog's most common
# categories; the ``other`` fallback handles the long tail
# (photo of vehicle / odometer statement / Buyer's Guide / driver's
# license copy / trade payoff verification / deal recap / CPI
# disclosure) until operator evidence surfaces need for structured
# subtypes.
STIP_TYPE_PROOF_OF_INCOME = "proof_of_income"
STIP_TYPE_PROOF_OF_INSURANCE = "proof_of_insurance"
STIP_TYPE_PROOF_OF_RESIDENCE = "proof_of_residence"
STIP_TYPE_REFERENCES = "references"
STIP_TYPE_OTHER = "other"

STIPULATION_TYPE_CHOICES = (
    (STIP_TYPE_PROOF_OF_INCOME, "Proof of income"),
    (STIP_TYPE_PROOF_OF_INSURANCE, "Proof of insurance"),
    (STIP_TYPE_PROOF_OF_RESIDENCE, "Proof of residence"),
    (STIP_TYPE_REFERENCES, "References"),
    (STIP_TYPE_OTHER, "Other"),
)

# Stipulation state vocabulary per MILESTONE_10_PLANNING.md §1.4.b
# Option A (user-confirmed at SESSION_109 open, recorded in §0.a).
# Fixed three-value set matching FINANCE §1.9 workflow. "Stip
# creep" manifests as new stip rows opened after previous ones
# cleared, not as a state transition on existing rows.
STIPULATION_STATE_OPEN = "open"
STIPULATION_STATE_CLEARED = "cleared"
STIPULATION_STATE_WAIVED = "waived"

STIPULATION_STATE_CHOICES = (
    (STIPULATION_STATE_OPEN, "Open (evidence outstanding)"),
    (STIPULATION_STATE_CLEARED, "Cleared (evidence provided)"),
    (STIPULATION_STATE_WAIVED, "Waived (lender no longer requires)"),
)


class Stipulation(models.Model):
    """Milestone 10 · Increment 4 — a lender-required stipulation.

    Persists the F&I workflow of tracking lender-required
    stipulations per FINANCE §1.9 — additional documents / actions
    the lender wants *in addition to* the signed contract before
    they will fund the deal. Per FINANCE §7.3 F&I is typically
    managing 15-40 open deals with various stip states at any
    given moment.

    **Attach shape — mandatory FK to LenderSubmission (CASCADE)**
    per ``MILESTONE_10_PLANNING.md`` §1.4.a Option A (user-
    confirmed at SESSION_109 open, recorded in §0.a). Stips are
    lender-specific per FINANCE §1.9 — every stip belongs to
    exactly one submission. Deleting a submission cascades to its
    stips. Deal-level pre-delivery items (insurance verification,
    odometer statement) belong to M9.2 :class:`Delivery`'s
    checklist, not to this tracker.

    **State machine.** ``open`` (default) → ``cleared`` (customer
    produced the evidence) OR ``waived`` (lender no longer
    requires). Any-to-any transition allowed at M10.4 (matches
    M10.3 :func:`services.f_and_i.update_lender_submission_status`
    posture — operator behavior captured as-recorded). The
    :func:`services.f_and_i.stipulation.update_stipulation_state`
    verb auto-populates :attr:`cleared_at` on transition to
    ``cleared`` / ``waived`` and clears it on transition back to
    ``open`` (rare — usually an operator error correction).

    **`documented_by` FK to User (nullable, SET_NULL).** Per
    §1.4.c Option A — audit-trail rigor. The F&I manager who
    cleared the stip is traceable. Nullable because a fresh stip
    hasn't been cleared yet. ``SET_NULL`` on user delete preserves
    historical stip rows when a user leaves the dealership.

    **No photo / document evidence at M10.4.** Per §1.4.d Option
    A — deferred to M10.7 compliance layer. Operators record
    "photo emailed to lender"-style evidence in the free-text
    ``notes`` field until the M10.7 layer adds structured
    storage plumbing.

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches ``lender_submission.dealership``. Belt (model) +
    suspenders (service layer's
    :class:`services.f_and_i.CrossTenantStipulationError`).
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="stipulations",
    )
    lender_submission = models.ForeignKey(
        "LenderSubmission",
        on_delete=models.CASCADE,
        related_name="stipulations",
    )
    stip_type = models.CharField(
        max_length=32,
        choices=STIPULATION_TYPE_CHOICES,
    )
    state = models.CharField(
        max_length=16,
        choices=STIPULATION_STATE_CHOICES,
        default=STIPULATION_STATE_OPEN,
    )
    documented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stipulations_documented",
    )
    # Populated automatically by the service verb when the state
    # transitions to ``cleared`` or ``waived``. Reset to NULL if
    # the state transitions back to ``open`` (operator error
    # correction path).
    cleared_at = models.DateTimeField(null=True, blank=True)
    # Milestone 10 · Increment 7 (SESSION_112) — external document
    # reference per §1.8.c Option C (user-confirmed at SESSION_112
    # open, recorded in §0.a). URL to the evidence document
    # (paystub scan, insurance card image, POR photo, etc.) in
    # the dealer's existing document system (Google Drive, DMS,
    # etc.). No storage plumbing at M10.7 — the URL field
    # captures operator reality without adding upload
    # infrastructure.
    evidence_url = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Stipulation"
        verbose_name_plural = "Stipulations"

    def __str__(self) -> str:
        return (
            f"Stipulation #{self.pk} — {self.get_stip_type_display()} "
            f"({self.get_state_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer.

        The denormalized ``dealership`` FK must match the parent
        LenderSubmission's tenant. Mirrors
        :meth:`LenderSubmission.clean` / :meth:`DealStructure.clean`.
        Data-scoping is layer 4 in ``AUTHENTICATION_MODEL.md`` §1.
        """
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.lender_submission_id is not None
            and self.lender_submission.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lender_submission": (
                        "Stipulation.lender_submission must belong to "
                        "the same dealership as the Stipulation. "
                        "Cross-tenant contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 5 (SESSION_110) — Contract + BackEndProductAgreement
#                                             + Funding vocabulary.
# ---------------------------------------------------------------------------

# Contract type vocabulary per MILESTONE_10_PLANNING.md §1.5 Option
# A + planning-time intent. Three values covering the RISC / lease /
# cash split. Extensions (`wholesale`, `internal_transfer`) land
# when operator evidence surfaces need.
CONTRACT_TYPE_RISC = "risc"
CONTRACT_TYPE_LEASE = "lease"
CONTRACT_TYPE_CASH = "cash"

CONTRACT_TYPE_CHOICES = (
    (CONTRACT_TYPE_RISC, "Retail Installment Sale Contract"),
    (CONTRACT_TYPE_LEASE, "Lease"),
    (CONTRACT_TYPE_CASH, "Cash"),
)

# Contract state vocabulary per MILESTONE_10_PLANNING.md §1.5.b
# Option A (user-confirmed at SESSION_110 open, recorded in §0.a).
# Three states: unsigned (default) → signed → optional voided.
# ``voided`` preserves the audit trail for FINANCE §5.8 deal
# unwinds — never delete a signed contract row.
CONTRACT_STATE_UNSIGNED = "unsigned"
CONTRACT_STATE_SIGNED = "signed"
CONTRACT_STATE_VOIDED = "voided"

CONTRACT_STATE_CHOICES = (
    (CONTRACT_STATE_UNSIGNED, "Unsigned (drafted)"),
    (CONTRACT_STATE_SIGNED, "Signed"),
    (CONTRACT_STATE_VOIDED, "Voided"),
)

# BackEndProductAgreement product-type vocabulary per
# MILESTONE_10_PLANNING.md §1.5.d Option A (user-confirmed at
# SESSION_110 open, recorded in §0.a). Fixed 6-value set covering
# the FINANCE §4.3-§4.5 catalog with an ``other`` fallback for the
# long tail (credit insurance, key replacement, windshield
# replacement, VIN etch, etc.). Extensions land when operator
# evidence surfaces need for structured subtypes.
BEPA_TYPE_VSC = "vsc"
BEPA_TYPE_GAP = "gap"
BEPA_TYPE_T_AND_W = "t_and_w"
BEPA_TYPE_PREPAID_MAINT = "prepaid_maint"
BEPA_TYPE_APPEARANCE = "appearance"
BEPA_TYPE_OTHER = "other"

BEPA_TYPE_CHOICES = (
    (BEPA_TYPE_VSC, "Vehicle Service Contract"),
    (BEPA_TYPE_GAP, "GAP (Guaranteed Asset Protection)"),
    (BEPA_TYPE_T_AND_W, "Tire & Wheel"),
    (BEPA_TYPE_PREPAID_MAINT, "Prepaid maintenance"),
    (BEPA_TYPE_APPEARANCE, "Appearance / paintless dent repair"),
    (BEPA_TYPE_OTHER, "Other"),
)

# Funding state vocabulary per MILESTONE_10_PLANNING.md §1.6.a
# Option C. Three states: pending_funding (default) → funded →
# optional chargedback (transition wired at M10.6 when Chargeback
# entity lands). ``chargedback`` shipped in the vocabulary at
# M10.5 so M10.6 needs no data migration — the M10.6 verb just
# adds the transition rule.
FUNDING_STATE_PENDING = "pending_funding"
FUNDING_STATE_FUNDED = "funded"
FUNDING_STATE_CHARGEDBACK = "chargedback"

FUNDING_STATE_CHOICES = (
    (FUNDING_STATE_PENDING, "Pending funding"),
    (FUNDING_STATE_FUNDED, "Funded"),
    (FUNDING_STATE_CHARGEDBACK, "Chargedback (M10.6)"),
)


class Contract(models.Model):
    """Milestone 10 · Increment 5 — signed contract row.

    Memorializes the signed retail installment / lease / cash
    contract for a :class:`DealStructure`. Per
    ``MILESTONE_10_PLANNING.md`` §1.5 + §1.5.b Option A + §1.5.c
    Option A (user-confirmed at SESSION_110 open, recorded in
    §0.a). The contract row is the persistent record of the
    Reg Z-disclosed financial terms as they appeared on the
    signed paper — distinct from the DealStructure's operator-
    entered pre-signing math (which may vary as F&I iterates).

    **Attach shape — mandatory FK to DealStructure (CASCADE)**
    per §1.5.c Option A. Cash contracts have a DealStructure but
    no LenderSubmission; operators navigate
    ``DealStructure.lender_submissions`` to find the approved
    lender submission for financed deals.

    **State machine.** ``unsigned`` (default) → ``signed`` →
    optional ``voided``. Two distinct service verbs handle the
    transitions:
    :func:`services.f_and_i.contract.sign_contract` populates
    ``signed_at``;
    :func:`services.f_and_i.contract.void_contract` populates
    ``voided_at`` + ``voided_reason``. Voided contracts preserve
    the audit trail for FINANCE §5.8 deal unwinds.

    **Reg Z-disclosed fields.** ``financed_amount``,
    ``total_of_payments``, ``finance_charge``, ``apr_disclosure``
    are the four Truth in Lending Act mandatory disclosures per
    FINANCE §6.1. Stored as-entered from the signed paper —
    the platform memorializes the disclosure, it does not
    recompute (finance_charge may differ slightly from a
    computed value due to fee amortization).

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches ``deal_structure.dealership``. Belt (model) +
    suspenders (service layer's
    :class:`services.f_and_i.CrossTenantContractError`).

    **Cash contracts.** ``contract_type=cash`` typically has
    ``financed_amount=0``, ``finance_charge=0``, and no
    ``first_payment_date``. The service verb doesn't enforce
    cross-field consistency at M10.5 — it trusts the operator to
    match the paper contract. If M10.7 compliance evidence
    surfaces need, transition rules can be added.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    deal_structure = models.ForeignKey(
        "DealStructure",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    contract_type = models.CharField(
        max_length=16,
        choices=CONTRACT_TYPE_CHOICES,
    )
    state = models.CharField(
        max_length=16,
        choices=CONTRACT_STATE_CHOICES,
        default=CONTRACT_STATE_UNSIGNED,
    )
    # Printed name of the customer / co-buyer who signed. Free-text
    # because a contract may be co-signed and the printed names on
    # paper may differ from the CreditApplication's applicant_full_name
    # (nicknames, married-name variations, etc.).
    signer_name = models.CharField(max_length=255, blank=True, default="")
    signed_at = models.DateTimeField(null=True, blank=True)
    # Reg Z Truth in Lending Act mandatory disclosures. Stored as-
    # entered from the signed paper; the platform memorializes
    # disclosure, it does not recompute.
    financed_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_of_payments = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    finance_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    # Percent units (matches ``payment_engine`` and
    # ``DealStructure.apr`` conventions). Default 0.0000 handles
    # cash contracts (no APR disclosure required).
    apr_disclosure = models.DecimalField(
        max_digits=6, decimal_places=4, default=Decimal("0.0000")
    )
    first_payment_date = models.DateField(null=True, blank=True)
    # Voided-state fields — populated only when state transitions
    # to ``voided``. ``voided_at`` auto-populated by the service
    # verb; ``voided_reason`` operator-provided (deal unwind
    # rationale per FINANCE §5.8).
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Contract"
        verbose_name_plural = "Contracts"

    def __str__(self) -> str:
        return (
            f"Contract #{self.pk} — {self.get_contract_type_display()} "
            f"for DS #{self.deal_structure_id} ({self.get_state_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer.

        The denormalized ``dealership`` FK must match the parent
        DealStructure's tenant. Mirrors :meth:`Sale.clean` /
        :meth:`Delivery.clean` / :meth:`CreditApplication.clean`.
        Data-scoping is layer 4 in ``AUTHENTICATION_MODEL.md`` §1.
        """
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.deal_structure_id is not None
            and self.deal_structure.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "deal_structure": (
                        "Contract.deal_structure must belong to the same "
                        "dealership as the Contract. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


class BackEndProductAgreement(models.Model):
    """Milestone 10 · Increment 5 — per-product agreement row on a Contract.

    Persists a single back-end product (VSC / GAP / T&W /
    prepaid maintenance / appearance / other) sold on a
    :class:`Contract`. Per
    ``MILESTONE_10_PLANNING.md`` §1.5.a Option B + §1.5.d
    Option A (both user-confirmed at SESSION_110 open, recorded
    in §0.a). Per-product rows enable per-product chargeback
    attribution at M10.6 per FINANCE §5.7.

    **Attach shape — FK to Contract (CASCADE).** Deleting a
    contract cascades to its product agreements. Multiple
    products per contract expected (typical F&I upsell menu
    per FINANCE §4.8).

    **Fixed product_type vocabulary** per §1.5.d Option A. Small
    fixed set covering the FINANCE §4.3-§4.5 catalog with
    ``other`` fallback for the long tail (credit insurance, key
    replacement, windshield replacement, VIN etch, etc.).

    **Economics fields.** ``cost`` (store's cost from provider) +
    ``retail_price`` (customer-paid price) are the base at-write
    economics. Optional structural fields (``term_months``,
    ``mileage_limit``, ``deductible``) apply per-product per
    FINANCE §4.3-§4.5 (VSCs have term + mileage + deductible;
    GAP is flat; T&W is term-only; etc.). ``provider`` (third-
    party administrator name — Zurich / JM&A / etc.) is free-
    text since provider catalogs are per-dealership and would
    duplicate the M10.3 LenderProgram pattern without
    proportionate benefit at M10.5.

    **Cancellation fields deferred to M10.6.** Per §0.a
    resolution — ``cancelled_at`` + ``cancellation_amount`` are
    M10.6 Chargeback concerns and land there. M10.5 ships the
    at-write economics only.

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches ``contract.dealership``. Belt + suspenders per
    project pattern.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="back_end_product_agreements",
    )
    contract = models.ForeignKey(
        "Contract",
        on_delete=models.CASCADE,
        related_name="back_end_products",
    )
    product_type = models.CharField(
        max_length=32,
        choices=BEPA_TYPE_CHOICES,
    )
    # Third-party administrator name (Zurich / JM&A / etc.). Free-
    # text at M10.5 — per-dealership provider catalogs deferred
    # until operator evidence surfaces need.
    provider = models.CharField(max_length=255, blank=True, default="")
    # Store's cost from the provider.
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    # Customer-paid retail price.
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Optional per-product structural fields. VSCs have all three;
    # GAP typically has none; T&W has term_months only.
    term_months = models.PositiveIntegerField(null=True, blank=True)
    mileage_limit = models.PositiveIntegerField(null=True, blank=True)
    deductible = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Milestone 10 · Increment 6 (SESSION_111) — additive
    # cancellation-tracking extension per §1.7.c Option A (user-
    # confirmed at SESSION_111 open, recorded in §0.a). Populated
    # by the M10.6 chargeback service verb when
    # ``chargeback_type=product_cancellation`` and the ``bepa``
    # FK is set on the Chargeback. Both fields nullable so M10.5-
    # era rows survive with NULL — the M10.6 pattern mirrors the
    # M10.2 additive extension of M10.1's CreditApplication
    # income columns.
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Milestone 10 · Increment 7 (SESSION_112) — external document
    # reference per §1.8.c Option C (user-confirmed at SESSION_112
    # open, recorded in §0.a). URL to the customer-signed product
    # agreement in the dealer's existing document system (Google
    # Drive, DMS, etc.). No storage plumbing at M10.7 — the URL
    # field captures operator reality (docs live in existing
    # systems) without adding upload infrastructure.
    product_agreement_url = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Back-end product agreement"
        verbose_name_plural = "Back-end product agreements"

    def __str__(self) -> str:
        return (
            f"BackEndProductAgreement #{self.pk} — "
            f"{self.get_product_type_display()} on Contract "
            f"#{self.contract_id} (retail ${self.retail_price})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer."""
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.contract_id is not None
            and self.contract.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "contract": (
                        "BackEndProductAgreement.contract must belong "
                        "to the same dealership as the agreement. "
                        "Cross-tenant contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


class Funding(models.Model):
    """Milestone 10 · Increment 5 — funding lifecycle row.

    Persists the funding lifecycle for a :class:`Contract` per
    ``MILESTONE_10_PLANNING.md`` §1.6.a Option C (user-confirmed
    at SESSION_110 open, recorded in §0.a). Single entity — no
    persisted FundingPacket per §1.6.a resolution (the packet
    is a per-submission view computable from Contract +
    Stipulation + related rows; M10.7 compliance layer can
    materialize a packet report if operators need one).

    **Attach shape — OneToOne to Contract (CASCADE).** Business
    invariant: one funding record per contract. Unwinds / re-
    signs (FINANCE §5.8) require a new Contract row rather than
    a fresh Funding attached to the same Contract — this keeps
    the audit trail clean and prevents ambiguity about which
    funding "belongs" to which signed contract.

    **State machine.** ``pending_funding`` (default) →
    ``funded`` → optional ``chargedback`` (transition wired at
    M10.6 when Chargeback entity lands). ``chargedback`` is
    included in the vocabulary at M10.5 so M10.6 needs no data
    migration; only the M10.6 verb adds the transition rule.

    **Auto-populated timestamps.** ``funded_at`` populated by
    :func:`services.f_and_i.funding.mark_funded` on transition
    to ``funded``. ``submitted_to_lender_at`` operator-provided
    at record time (or defaults to now).

    **`funding_amount` nullable.** Populated only when state
    transitions to ``funded`` — before that, the amount is
    unknown (may differ from ``Contract.financed_amount`` due to
    lender discount fees per FINANCE §2.4).

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches ``contract.dealership``. Belt + suspenders.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="fundings",
    )
    contract = models.OneToOneField(
        "Contract",
        on_delete=models.CASCADE,
        related_name="funding",
    )
    state = models.CharField(
        max_length=32,
        choices=FUNDING_STATE_CHOICES,
        default=FUNDING_STATE_PENDING,
    )
    submitted_to_lender_at = models.DateTimeField(null=True, blank=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    # Actual amount funded — may differ from Contract.financed_amount
    # due to lender discount fees (per FINANCE §2.4). NULL until
    # the state transitions to ``funded``.
    funding_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Funding"
        verbose_name_plural = "Fundings"

    def __str__(self) -> str:
        return (
            f"Funding #{self.pk} — Contract #{self.contract_id} "
            f"({self.get_state_display()})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer."""
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.contract_id is not None
            and self.contract.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "contract": (
                        "Funding.contract must belong to the same "
                        "dealership as the Funding. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 6 (SESSION_111) — Chargeback vocabulary.
# ---------------------------------------------------------------------------

# Chargeback type vocabulary per MILESTONE_10_PLANNING.md §1.7.b
# Option B (user-confirmed at SESSION_111 open, recorded in §0.a).
# Five FINANCE §5.7 triggers plus an ``other`` fallback matching
# the M10.1 §5.b + M10.3 §1.3.b + M10.4 §5.b + M10.5 §1.5.d
# vocab-with-other pattern.
CHARGEBACK_TYPE_FPD = "first_payment_default"
CHARGEBACK_TYPE_EARLY_PAYOFF = "early_payoff"
CHARGEBACK_TYPE_PRODUCT_CANCELLATION = "product_cancellation"
CHARGEBACK_TYPE_REPOSSESSION = "repossession"
CHARGEBACK_TYPE_DEAL_UNWIND = "deal_unwind"
CHARGEBACK_TYPE_OTHER = "other"

CHARGEBACK_TYPE_CHOICES = (
    (CHARGEBACK_TYPE_FPD, "First payment default"),
    (CHARGEBACK_TYPE_EARLY_PAYOFF, "Early payoff"),
    (CHARGEBACK_TYPE_PRODUCT_CANCELLATION, "Product cancellation"),
    (CHARGEBACK_TYPE_REPOSSESSION, "Repossession"),
    (CHARGEBACK_TYPE_DEAL_UNWIND, "Deal unwind"),
    (CHARGEBACK_TYPE_OTHER, "Other"),
)

# Deal-level chargeback types per FINANCE §5.7 — these undo the
# funding and cause the associated Funding row to auto-transition
# to ``chargedback`` state per §1.7.f Option A. ``product_cancellation``
# is explicitly excluded (reduces commission but leaves the deal
# funded). ``other`` is also excluded (safer default — operators
# explicitly mark the Funding chargedback via separate PATCH for
# novel-type chargebacks).
DEAL_LEVEL_CHARGEBACK_TYPES = frozenset(
    (
        CHARGEBACK_TYPE_FPD,
        CHARGEBACK_TYPE_EARLY_PAYOFF,
        CHARGEBACK_TYPE_REPOSSESSION,
        CHARGEBACK_TYPE_DEAL_UNWIND,
    )
)


class Chargeback(models.Model):
    """Milestone 10 · Increment 6 — chargeback event row.

    Persists a lender-driven chargeback event per FINANCE §5.7 —
    when the lender reverses part or all of the dealer's
    compensation on a funded deal because something subsequently
    went wrong (FPD, early payoff, product cancellation,
    repossession, deal unwind, or other).

    **Attach shape — nullable FKs to both Contract and BEPA**
    per ``MILESTONE_10_PLANNING.md`` §1.7.a Option A (user-
    confirmed at SESSION_111 open, recorded in §0.a). Mirrors
    the M10.1 §5.a Option C precedent. ``clean()`` requires at
    least one of the two to be set. Product-cancellation
    chargebacks are conceptually attached to both — the
    contract's funding is adjusted AND the specific BEPA's
    commission is pro-rated.

    **Fixed type vocabulary** per §1.7.b Option B. Six values:
    FINANCE §5.7's five triggers plus ``other``.

    **Audit trail.** ``recorded_by`` FK to
    ``settings.AUTH_USER_MODEL`` nullable, SET_NULL on user
    delete per §1.7.e Option A + the M10.4 ``documented_by``
    pattern. Sourced from ``request.user`` at the endpoint
    layer. ``chargeback_date`` is the operator-provided
    business date (may predate row insert if backfilled);
    ``created_at`` is the row insert timestamp.

    **Funding auto-transition side effect.** Per §1.7.f Option
    A the service verb :func:`services.f_and_i.record_chargeback`
    auto-transitions the associated Funding row to
    ``chargedback`` state when ``chargeback_type`` is one of the
    four deal-level types (see
    :data:`DEAL_LEVEL_CHARGEBACK_TYPES`). ``product_cancellation``
    and ``other`` chargebacks do not touch Funding state.

    **BEPA cancellation-field auto-populate side effect.** When
    ``chargeback_type=product_cancellation`` and ``bepa`` FK is
    set, the service verb populates
    ``BackEndProductAgreement.cancelled_at`` (from
    ``chargeback_date``) + ``cancellation_amount`` (from
    ``chargeback_amount``).

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches whichever parent FK is set — ``contract.dealership``
    if ``contract`` is set, ``bepa.dealership`` if ``bepa`` is
    set. Both may be set (product cancellation); both must
    match the chargeback's own tenant. Belt + suspenders per
    project pattern.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="chargebacks",
    )
    # §1.7.a Option A: nullable FKs to both. clean() requires
    # at least one. CASCADE on both — a chargeback attached to
    # a deleted parent has no attribution and shouldn't survive.
    contract = models.ForeignKey(
        "Contract",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chargebacks",
    )
    bepa = models.ForeignKey(
        "BackEndProductAgreement",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chargebacks",
    )
    chargeback_type = models.CharField(
        max_length=32,
        choices=CHARGEBACK_TYPE_CHOICES,
    )
    # Operator-provided business date (may predate row insert if
    # backfilled from a lender statement).
    chargeback_date = models.DateField()
    # Amount reversed. Stored as a positive Decimal — the sign
    # is implicit (chargebacks always reduce realized revenue).
    # The ``services.f_and_i.chargeback.net_realized`` verb
    # subtracts these amounts from ``Sale.gross_realized``.
    chargeback_amount = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    # §1.7.e Option A: FK to User nullable SET_NULL. Sourced
    # from ``request.user`` at the endpoint layer per M10.4
    # server-side audit-trail pattern.
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chargebacks_recorded",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-chargeback_date", "-created_at")
        verbose_name = "Chargeback"
        verbose_name_plural = "Chargebacks"

    def __str__(self) -> str:
        return (
            f"Chargeback #{self.pk} — "
            f"{self.get_chargeback_type_display()} "
            f"(${self.chargeback_amount} on {self.chargeback_date})"
        )

    def clean(self) -> None:
        """Cross-tenant contamination + attach-shape guards.

        Three invariants:

        1. At least one of ``contract`` / ``bepa`` is set — a
           chargeback with both FKs null has no attribution.
        2. When ``contract`` is set,
           ``contract.dealership`` must match ``dealership``.
        3. When ``bepa`` is set, ``bepa.dealership`` must match
           ``dealership``.
        """
        super().clean()
        if self.dealership_id is None:
            return
        if self.contract_id is None and self.bepa_id is None:
            raise ValidationError(
                {
                    "__all__": (
                        "Chargeback must attach to at least one of "
                        "contract or bepa (see MILESTONE_10_PLANNING.md "
                        "§1.7.a Option A)."
                    )
                }
            )
        if (
            self.contract_id is not None
            and self.contract.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "contract": (
                        "Chargeback.contract must belong to the same "
                        "dealership as the Chargeback. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )
        if (
            self.bepa_id is not None
            and self.bepa.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "bepa": (
                        "Chargeback.bepa must belong to the same "
                        "dealership as the Chargeback. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 7 (SESSION_112) — ComplianceRecord.
# ---------------------------------------------------------------------------


class ComplianceRecord(models.Model):
    """Milestone 10 · Increment 7 — deal-jacket compliance record.

    Persists the compliance-audit state for a signed
    :class:`Contract`. Per FINANCE §6.9 the deal jacket is the
    operational record of retention; per ``MILESTONE_10_PLANNING.md``
    §1.8.a Option A (user-confirmed at SESSION_112 open, recorded
    in §0.a) the ComplianceRecord is a per-Contract OneToOne row
    that memorializes which regulatory events happened, when, and
    by whom.

    **Attach shape — OneToOne to Contract (CASCADE)** per §1.8.a.
    Matches FINANCE §6.9 deal-jacket mental model. Pre-contract
    compliance events (OFAC check on CreditApplication, adverse-
    action notice on LenderSubmission) surface via the operator
    UI without requiring their own ComplianceRecord — the
    operator UI aggregates across those entities in the deal-
    jacket summary view.

    **Single-entity typed-columns model** per §1.8.b Option A.
    FINANCE §6.1-§6.9 defines seven regulatory concerns; each
    gets a small set of named columns:

    - **Reg Z (§6.1)**: ``reg_z_disclosed_at`` — timestamp when
      Reg Z disclosures were reviewed with the customer.
    - **OFAC (§6.2)**: ``ofac_checked_at`` +
      ``ofac_hit`` (bool) — SDN screen result.
    - **Red Flags (§6.3)**: ``red_flags_reviewed_at`` +
      ``red_flags_notes`` (text) — ITPP review outcome.
    - **Privacy notice (§6.4)**: ``privacy_notice_delivered_at``.
    - **Safeguards audit (§6.4/§6.7)**:
      ``safeguards_audit_at`` — WISP review timestamp.
    - **Adverse action (§6.5)**: ``adverse_action_sent_at`` +
      ``adverse_action_reason`` (text). NULL when the deal
      closed on the approved terms (no adverse action taken).
    - **Retention (§6.9)**: ``retention_expires_at`` —
      denormalized from the parent CreditApplication for
      query-ability at the deal-jacket layer. The
      CreditApplication's own retention clock remains the model-
      layer invariant per M10.1 §5.e.

    **External deal-jacket URL** per §1.8.c Option C:
    ``deal_jacket_url`` for the operator's shared document
    system (Google Drive folder, DMS deal jacket, etc.). No
    upload plumbing at M10.7 — full storage infrastructure
    (Cloudinary/S3 + presigned URLs + MIME validation) is a
    discrete post-M10 initiative.

    **Cross-tenant guard.** ``clean()`` enforces ``dealership``
    matches ``contract.dealership``. Belt + suspenders per
    project pattern.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="compliance_records",
    )
    contract = models.OneToOneField(
        "Contract",
        on_delete=models.CASCADE,
        related_name="compliance_record",
    )
    # Reg Z (§6.1)
    reg_z_disclosed_at = models.DateTimeField(null=True, blank=True)
    # OFAC (§6.2)
    ofac_checked_at = models.DateTimeField(null=True, blank=True)
    ofac_hit = models.BooleanField(default=False)
    # Red Flags (§6.3)
    red_flags_reviewed_at = models.DateTimeField(null=True, blank=True)
    red_flags_notes = models.TextField(blank=True, default="")
    # Privacy notice (§6.4)
    privacy_notice_delivered_at = models.DateTimeField(null=True, blank=True)
    # Safeguards audit (§6.4 / §6.7)
    safeguards_audit_at = models.DateTimeField(null=True, blank=True)
    # Adverse action (§6.5). NULL when no adverse action was taken
    # (deal closed on approved terms). Populated when a decline /
    # counter-offer / co-signer requirement triggered the notice.
    adverse_action_sent_at = models.DateTimeField(null=True, blank=True)
    adverse_action_reason = models.TextField(blank=True, default="")
    # Retention (§6.9). Denormalized from CreditApplication for
    # deal-jacket query-ability. Populated by the service verb.
    retention_expires_at = models.DateTimeField(null=True, blank=True)
    # External document reference per §1.8.c Option C.
    deal_jacket_url = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Compliance record"
        verbose_name_plural = "Compliance records"

    def __str__(self) -> str:
        return (
            f"ComplianceRecord #{self.pk} — Contract "
            f"#{self.contract_id}"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer."""
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.contract_id is not None
            and self.contract.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "contract": (
                        "ComplianceRecord.contract must belong to the "
                        "same dealership as the ComplianceRecord. "
                        "Cross-tenant contamination guard (see "
                        "AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 11 · Increment 2 (SESSION_115) — TestDrive.
# ---------------------------------------------------------------------------


class TestDrive(models.Model):
    """Milestone 11 · Increment 2 — the test-drive record.

    Captures the demonstration / test-drive step of the sales workflow
    per ``SALES_DEPARTMENT_MAPPING.md`` §workflow step 6.

    **Attach shape — mandatory FKs to both `CustomerLead` and `Vehicle`**
    per ``MILESTONE_11_PLANNING.md`` §5.c Option A (user-confirmed at
    SESSION_114 open, recorded in §0.a). Rationale: the salesperson
    creates a lead at the handshake before the drive; there is no
    "vehicle demonstration without a specific customer" case in the
    documented workflow. If that case later surfaces from operator
    evidence, the FKs can be relaxed to nullable in a subsequent
    milestone.

    **CASCADE on both parents.** The test drive is a subsidiary
    record of the customer-vehicle interaction; if either parent
    is deleted the drive record loses its anchor. Neither
    `CustomerLead` nor `Vehicle` supports normal deletion in
    the current workflow (soft-null via `is_active` /
    `is_available`), so CASCADE is defensive.

    **Cross-tenant guard.** `clean()` enforces that both `lead` and
    `vehicle` belong to the same dealership as the drive. Belt (model)
    + suspenders (service layer's `CrossTenantTestDriveError`) — same
    posture as M10.1 credit-application.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="test_drives",
    )
    lead = models.ForeignKey(
        "CustomerLead",
        on_delete=models.CASCADE,
        related_name="test_drives",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="test_drives",
    )
    # Salesperson who accompanied the customer on the drive. SET_NULL
    # preserves the historical drive record when a User is deleted /
    # deactivated (same rationale as `Salesperson.user` at M1.4A).
    driven_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="test_drives_conducted",
    )
    driven_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    route_notes = models.TextField(blank=True, default="")
    customer_reaction = models.TextField(blank=True, default="")
    # Structured objection capture. JSON list, e.g. ["price too high",
    # "want AWD", "waiting for tax refund"]. The vocabulary is not
    # constrained at M11.2 — operator entries can be free-text list
    # items. A structured objection vocabulary lookup table is a M12
    # candidate once analytics need it (SALES §5 discovery vocab).
    objections_captured = models.JSONField(default=list, blank=True)
    next_action = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-driven_at"]

    def __str__(self) -> str:
        return (
            f"TestDrive #{self.pk} — lead #{self.lead_id} × "
            f"vehicle #{self.vehicle_id}"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer."""
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.lead_id is not None
            and self.lead.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lead": (
                        "TestDrive.lead must belong to the same "
                        "dealership as the TestDrive. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )
        if (
            self.vehicle_id is not None
            and self.vehicle.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "vehicle": (
                        "TestDrive.vehicle must belong to the same "
                        "dealership as the TestDrive. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 11 · Increment 3 (SESSION_116) — DealWriteup.
# ---------------------------------------------------------------------------


class DealWriteup(models.Model):
    """Milestone 11 · Increment 3 — the four-square deal write-up.

    Captures the sales-side deal write-up (four-square worksheet) per
    ``SALES_DEPARTMENT_MAPPING.md`` §workflow step 10. Links to the M10
    F&I workflow via the handoff action per §5.e Option A — the auto-
    creation of a matching :class:`CreditApplication` happens at the
    service layer (:func:`services.deal_writeups.hand_off_to_fandi`),
    keeping model layers thin.

    **Attach shape — mandatory FKs to both `CustomerLead` and `Vehicle`.**
    A deal write-up is always written for a specific customer on a
    specific vehicle; the "generic worksheet" case does not exist in
    the documented workflow. Same rationale as M11.2 TestDrive
    (§5.c Option A precedent).

    **Approval state.** ``sales_manager_approved_at`` /
    ``sales_manager_approved_by_user`` populated when the sales manager
    approves the four-square terms (sales-manager approval is the
    gate on the F&I hand-off in the real workflow). Nullable both —
    unapproved writeups are legitimate drafts.

    **Handoff link.** ``handed_off_to_fandi_at`` populated when the
    handoff verb fires. Not FK to CreditApplication — the CA row
    outlives the writeup for retention reasons (M10.1 §5.e locked
    retention clock; deleting the writeup must not cascade to the CA).
    The CA carries the reverse link via its own ``lead`` FK, which
    matches the writeup's lead.

    **Cross-tenant guard.** ``clean()`` enforces same-tenant lead +
    vehicle FKs. Belt (model) + suspenders (service).
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="deal_writeups",
    )
    lead = models.ForeignKey(
        "CustomerLead",
        on_delete=models.CASCADE,
        related_name="deal_writeups",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="deal_writeups",
    )
    # Four-square terms. All nullable — a writeup in progress may not
    # have every cell filled yet; the F&I handoff verb enforces that
    # the sales manager approved before the CA is auto-created, but
    # does not enforce which cells are populated (that's an operator
    # choice, not a system invariant).
    vehicle_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    trade_allowance = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    down_payment = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    monthly_payment_target = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    term_months_target = models.PositiveIntegerField(null=True, blank=True)
    # APR as a percentage (e.g. 7.49). Distinct from the M2 payment-
    # engine APR representation to keep the four-square captured
    # value separate from the deterministic math result.
    apr_target = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    write_up_at = models.DateTimeField()
    written_up_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deal_writeups_written",
    )
    sales_manager_approved_at = models.DateTimeField(null=True, blank=True)
    sales_manager_approved_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deal_writeups_approved",
    )
    handed_off_to_fandi_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-write_up_at"]

    def __str__(self) -> str:
        return (
            f"DealWriteup #{self.pk} — lead #{self.lead_id} × "
            f"vehicle #{self.vehicle_id}"
        )

    def clean(self) -> None:
        """Cross-tenant contamination guard at the model layer."""
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.lead_id is not None
            and self.lead.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lead": (
                        "DealWriteup.lead must belong to the same "
                        "dealership as the DealWriteup. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )
        if (
            self.vehicle_id is not None
            and self.vehicle.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "vehicle": (
                        "DealWriteup.vehicle must belong to the same "
                        "dealership as the DealWriteup. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 11 · Increment 4 (SESSION_117) — Follow-up cadence orchestration.
# ---------------------------------------------------------------------------


# Fixed template vocabulary per SESSION_117 §0.a M11.4 amendment
# (implementation-time default). Six named schedules mapping to the
# canonical follow-up windows named in MILESTONE_11_PLANNING.md §1.4.
# Each template is a fixed sequence of offsets (in days from cadence
# start) that :func:`services.follow_ups.start_cadence` uses to seed
# :class:`FollowUpTask` rows.
FOLLOW_UP_TEMPLATE_24HR = "24hr"
FOLLOW_UP_TEMPLATE_1WK = "1wk"
FOLLOW_UP_TEMPLATE_30DAY = "30day"
FOLLOW_UP_TEMPLATE_90DAY = "90day"
FOLLOW_UP_TEMPLATE_6MO = "6mo"
FOLLOW_UP_TEMPLATE_1YR = "1yr"

FOLLOW_UP_TEMPLATE_CHOICES = (
    (FOLLOW_UP_TEMPLATE_24HR, "24 hours"),
    (FOLLOW_UP_TEMPLATE_1WK, "1 week"),
    (FOLLOW_UP_TEMPLATE_30DAY, "30 days"),
    (FOLLOW_UP_TEMPLATE_90DAY, "90 days"),
    (FOLLOW_UP_TEMPLATE_6MO, "6 months"),
    (FOLLOW_UP_TEMPLATE_1YR, "1 year"),
)

# Offset schedules (days from cadence start) per template. Kept as a
# module-level constant so the seeding logic + tests share one source
# of truth. Fractional-day offsets use timedelta at the service layer.
FOLLOW_UP_TEMPLATE_OFFSETS: dict[str, tuple[float, ...]] = {
    FOLLOW_UP_TEMPLATE_24HR: (1.0,),
    FOLLOW_UP_TEMPLATE_1WK: (1.0, 3.0, 7.0),
    FOLLOW_UP_TEMPLATE_30DAY: (1.0, 3.0, 7.0, 14.0, 30.0),
    FOLLOW_UP_TEMPLATE_90DAY: (1.0, 7.0, 30.0, 60.0, 90.0),
    FOLLOW_UP_TEMPLATE_6MO: (7.0, 30.0, 90.0, 180.0),
    FOLLOW_UP_TEMPLATE_1YR: (30.0, 90.0, 180.0, 365.0),
}

# Task state vocabulary. Two terminal states (completed / skipped) +
# the initial state (pending). No auto-skip at M11.4 — the beat
# surfacer flags stale tasks in logs but never transitions state per
# SESSION_117 §0.a M11.4 amendment (decision 3).
FOLLOW_UP_TASK_STATE_PENDING = "pending"
FOLLOW_UP_TASK_STATE_COMPLETED = "completed"
FOLLOW_UP_TASK_STATE_SKIPPED = "skipped"

FOLLOW_UP_TASK_STATE_CHOICES = (
    (FOLLOW_UP_TASK_STATE_PENDING, "Pending"),
    (FOLLOW_UP_TASK_STATE_COMPLETED, "Completed"),
    (FOLLOW_UP_TASK_STATE_SKIPPED, "Skipped"),
)


class FollowUpCadence(models.Model):
    """Milestone 11 · Increment 4 — the follow-up cadence header.

    Per MILESTONE_11_PLANNING.md §1.4 + §5.d Option A (user-confirmed at
    SESSION_114 open, recorded in §0.a). Two-entity model —
    :class:`FollowUpCadence` is the header (one per lead per template
    instance); :class:`FollowUpTask` rows are the scheduled contact
    points. Cadence rows are queryable per-lead; task rows are the
    operator's primary work unit and queryable independently.

    **Idempotency (per-lead per-template).** The service verb
    :func:`services.follow_ups.start_cadence` refuses to create a
    duplicate active cadence for the same (lead, template) pair.
    Historical (paused / completed) cadences don't block a fresh
    start.

    **Pause semantics.** ``is_active=False`` halts future beat
    surfacing but leaves the task rows intact — an operator can
    resume by re-activating, or leave paused as a permanent record
    of the sequence attempted. Task-row deletion is never automatic.

    **Cross-tenant guard.** ``clean()`` enforces same-tenant `lead`.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="follow_up_cadences",
    )
    lead = models.ForeignKey(
        "CustomerLead",
        on_delete=models.CASCADE,
        related_name="follow_up_cadences",
    )
    template = models.CharField(
        max_length=16, choices=FOLLOW_UP_TEMPLATE_CHOICES
    )
    started_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return (
            f"FollowUpCadence #{self.pk} — lead #{self.lead_id} × "
            f"{self.template}"
        )

    def clean(self) -> None:
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.lead_id is not None
            and self.lead.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lead": (
                        "FollowUpCadence.lead must belong to the same "
                        "dealership as the cadence. Cross-tenant "
                        "contamination guard (see AUTHENTICATION_MODEL.md "
                        "§1 layer 4)."
                    )
                }
            )


class FollowUpTask(models.Model):
    """Milestone 11 · Increment 4 — a scheduled follow-up contact point.

    Rows seeded by :func:`services.follow_ups.start_cadence` at cadence
    creation using the template's offset schedule
    (:data:`FOLLOW_UP_TEMPLATE_OFFSETS`).

    **State machine.**

    - Initial: ``pending``.
    - ``pending`` → ``completed`` via
      :func:`services.follow_ups.complete_task`.
    - ``pending`` → ``skipped`` via
      :func:`services.follow_ups.skip_task`.
    - No auto-transitions at M11.4 (per SESSION_117 §0.a decision 3).

    **Beat surfacer** (M11.4 orchestrator) reads
    ``state=pending`` + ``due_at <= now()`` and logs the count, but
    doesn't mutate state — operator intent is required for every
    transition.

    **CASCADE on cadence delete.** Deleting a cadence removes its
    tasks. A pause + soft-null posture on the cadence is preferred
    to deletion.

    **Cross-tenant guard.** ``clean()`` enforces same-tenant
    ``cadence``.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="follow_up_tasks",
    )
    cadence = models.ForeignKey(
        FollowUpCadence,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    due_at = models.DateTimeField(db_index=True)
    state = models.CharField(
        max_length=16,
        choices=FOLLOW_UP_TASK_STATE_CHOICES,
        default=FOLLOW_UP_TASK_STATE_PENDING,
    )
    completed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="follow_up_tasks_completed",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at"]

    def __str__(self) -> str:
        return (
            f"FollowUpTask #{self.pk} — cadence #{self.cadence_id} "
            f"({self.state}, due {self.due_at.isoformat()})"
        )

    def clean(self) -> None:
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.cadence_id is not None
            and self.cadence.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "cadence": (
                        "FollowUpTask.cadence must belong to the same "
                        "dealership as the task. Cross-tenant contamination "
                        "guard (see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )


# ---------------------------------------------------------------------------
# Milestone 11 · Increment 5 (SESSION_118) — BeBack tracking.
# ---------------------------------------------------------------------------


# Reason vocabulary per SESSION_118 §0.a M11.5 amendment (decision 2 —
# Option A). Fixed 4+1 vocab matching the M11.1 vocab-set pattern.
BE_BACK_REASON_TEST_DRIVE = "test_drive"
BE_BACK_REASON_BRING_CO_SIGNER = "bring_co_signer"
BE_BACK_REASON_BRING_TRADE_IN = "bring_trade_in"
BE_BACK_REASON_OTHER = "other"

BE_BACK_REASON_CHOICES = (
    (BE_BACK_REASON_TEST_DRIVE, "Test drive"),
    (BE_BACK_REASON_BRING_CO_SIGNER, "Bring co-signer"),
    (BE_BACK_REASON_BRING_TRADE_IN, "Bring trade-in"),
    (BE_BACK_REASON_OTHER, "Other"),
)

# State machine per SALES §step 15. Two terminal states (returned /
# no_show) + the initial state (promised). No re-transitions once
# terminal — see :class:`services.be_backs.BeBackAlreadyTerminalError`.
BE_BACK_STATE_PROMISED = "promised"
BE_BACK_STATE_RETURNED = "returned"
BE_BACK_STATE_NO_SHOW = "no_show"

BE_BACK_STATE_CHOICES = (
    (BE_BACK_STATE_PROMISED, "Promised"),
    (BE_BACK_STATE_RETURNED, "Returned"),
    (BE_BACK_STATE_NO_SHOW, "No-show"),
)


class BeBack(models.Model):
    """Milestone 11 · Increment 5 — a customer promise-to-return record.

    Per MILESTONE_11_PLANNING.md §1.5 + SESSION_118 §0.a M11.5
    amendment. SALES §step 15 — customers who visit, don't buy, and
    promise to return are the largest single-source of eventual sales
    at mature stores (pain #15).

    **Attach shape (§5.g.1 Option A).** Mandatory FK to
    :class:`CustomerLead` (CASCADE). No FK to :class:`Vehicle` — a
    be-back is about returning to the store, not necessarily the same
    unit. Customers often return to negotiate a different vehicle or
    check trade-in valuation on a different candidate.

    **State machine.**

    - Initial: ``promised`` (customer said they'd return).
    - ``promised`` → ``returned`` via
      :func:`services.be_backs.mark_returned` (populates
      ``actual_return_at``).
    - ``promised`` → ``no_show`` via
      :func:`services.be_backs.mark_no_show` — auto-fired by the
      M11.5 Celery detector at 07:00 daily when ``promised_at +
      grace_period`` passes without ``actual_return_at``. Also
      exposed as an operator-triggered endpoint.
    - No re-transitions from terminal states.

    **Cross-tenant guard.** ``clean()`` enforces same-tenant `lead`.
    """

    dealership = models.ForeignKey(
        "Dealership",
        on_delete=models.CASCADE,
        related_name="be_backs",
    )
    lead = models.ForeignKey(
        "CustomerLead",
        on_delete=models.CASCADE,
        related_name="be_backs",
    )
    promised_at = models.DateTimeField(
        help_text="When the customer said they would return.",
    )
    promised_reason = models.CharField(
        max_length=32, choices=BE_BACK_REASON_CHOICES
    )
    actual_return_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(
        max_length=16,
        choices=BE_BACK_STATE_CHOICES,
        default=BE_BACK_STATE_PROMISED,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-promised_at"]

    def __str__(self) -> str:
        return (
            f"BeBack #{self.pk} — lead #{self.lead_id} "
            f"({self.state}, promised {self.promised_at.isoformat()})"
        )

    def clean(self) -> None:
        super().clean()
        if self.dealership_id is None:
            return
        if (
            self.lead_id is not None
            and self.lead.dealership_id != self.dealership_id
        ):
            raise ValidationError(
                {
                    "lead": (
                        "BeBack.lead must belong to the same dealership "
                        "as the BeBack. Cross-tenant contamination guard "
                        "(see AUTHENTICATION_MODEL.md §1 layer 4)."
                    )
                }
            )
