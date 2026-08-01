import uuid
from datetime import date
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
