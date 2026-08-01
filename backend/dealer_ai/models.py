import uuid
from datetime import date
from functools import cached_property
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
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
